import collections
import fnmatch
import os
# import re
from typing import Any, Dict, List, Set

import bsp_tool
import valvefgd


# TODO: refactor to work for any game & fgd combination
# TODO: use variables instead of globals
r1md = "/media/bikkie/3964-3935/Mod/Titanfall/maps"
p2fd = "/media/bikkie/3964-3935/Mod/Portal2/bin/base.fgd"

fgd = valvefgd.FgdParse(p2fd)
fgd_ents = [e.name for e in fgd.entities]


def ur_ent(**filters: Dict[str, str]) -> Dict[str, Set[str]]:
    """Find 'ur' entity (all keys & values used in official maps)"""
    # TODO: take cached maps: Dict[str, bsp_tool.Bsp] as an argument
    # NOTE: will get a handful of false positives from renamed ents w/ forgotten key values
    out = collections.defaultdict(set)
    for map_name in fnmatch.filter(os.listdir(r1md), "*.bsp"):
        print("scanning", map_name)
        bsp = bsp_tool.load_bsp(os.path.join(r1md, map_name))
        for ent in sum(bsp.search_all_entities(**filters).values(), start=list()):
            for key, value in ent.items():
                if key in ("classname", "spawnflags"):
                    continue
                out[key].add(value)
            break  # HACK: gotta test fast
        break  # HACK: gotta test fast
    return {k: sorted(out[k]) for k in sorted(out)}


def id_ent(classname: str = None, **filters: Dict[str, str]) -> Dict[str, Set[str]]:
    """build entity dossier"""
    if classname is not None:
        filters["classname"] = classname
    assert "classname" in filters
    ent_class = filters["classname"]
    ue = ur_ent(**filters)
    ue_keys = set(ue.keys())
    out = {"classname": ent_class, "ur": ue, "type": "point", "spec": None, "old": set(), "new": ue_keys}
    if ent_class not in fgd_ents:
        out["origin"] = "Titanfall"
        if any([v.startswith("*") for v in ue.get("model", list())]):  # brush entity
            out["new"].remove("model")
            out["type"] = "group"
        if "origin" in out["new"]:  # automatically added by Radiant
            out["new"].remove("origin")
        return out
    # TODO: catch editorclass / spawnclass subtype
    fe = fgd.entity_by_name(ent_class)
    fe_keys = {p.name for p in fe.properties}
    out.update({"origin": "Source",
                "type": {"PointClass": "point", "SolidClass": "group"}[fe.class_type],
                "new": ue_keys.difference({*fe_keys, "origin"}),
                "old": fe_keys.difference({*ue_keys, "origin"}),
                "spec": fe})
    return out


# .ent (XML) assemblers
def camelCase(snake_case: str) -> str:
    """choice type name formatter"""
    out = list()
    for word in snake_case.split("_"):
        out.append(word[0].upper() + word[1:])
    out = "".join(out)
    return out[0].lower() + out[1:]


def xml_choices(choice_property: valvefgd.FgdEntityProperty) -> (str, str):
    type_name = camelCase(choice_property.name)
    out = [f'<list name="{type_name}">']
    for choice in choice_property.choices:
        out.append(f'  <item ="{choice.display_name}" value="{choice.value}"/>')
    out.append("</list>")
    return type_name, "\n".join(out)


log2 = {2 ** i: i for i in range(32)}  # for spawnflags conversion


def xml_spawnflags(spawnflags: List[valvefgd.FgdEntitySpawnflag]) -> str:
    out = list()
    for flag in spawnflags:
        # flag.display_name, value, default_value
        name = "_".join(["FLAG", *map(str.upper, flag.display_name.split())])
        bit = log2[flag.value]
        default = int(flag.default_value)
        out.append(f'<flag name="{name}" bit="{bit}" value="{default}">TODO: get description from VDC</flag>')
    return out


def ent_definitions(ent_spec: valvefgd.FgdEntity) -> Dict[str, Dict[str, Any]]:
    out = dict()
    ancestors = list(ent_spec.parents)
    for ancestor in ancestors:
        ancestors.extend(ancestor.parents)  # keep digging
        for defs in getattr(ancestor, "defintions", list()):
            for d in defs:
                if d["name"] not in out:  # newest overrides
                    out[d["name"]] = d["args"][0]
    return out


key_types = {"float": "real", "boolean": "boolean", "integer": "integer", "studio": "model",
             "sound": "sound", "target_source": "targetname", "target_dest": "targetname"}
# ^ fgd_key key_type


def guess_key_type(key_name: str, key_values: Set[str]) -> str:
    """ur_key key_type"""
    is_vec3, is_vec4, is_path = False, False, False
    if key_name.lower() == "scale":
        return "real"
    # TODO: regex numbers
    if all(map(lambda v: v.count(" ") == 3, key_values)):
        is_vec3 = True
    if all(map(lambda v: v.count(" ") == 4, key_values)):
        is_vec4 = True
    if any(map(lambda v: "/" in v.replace("\\", "/"), key_values)):
        is_path = True
    if "color" in key_name.lower() and is_vec3 and not is_vec4:
        return "color"
    if "model" in key_name.lower() and is_path:
        return "model"
    if "target" in key_name.lower():  # TEST: false positives
        return "targetname"
    return "string"


def xml_ent(classname: str = None, **filters: Dict[str, str]) -> (str, Set[str]):
    out = list()
    choice_types = set()
    dossier = id_ent(classname, **filters)
    defs = ent_definitions(dossier["spec"]) if dossier["spec"] is not None else dict()
    head = f"<{dossier['type']} name=\"{dossier['classname']}\""
    color = " ".join(map(str, defs.get("color", [1, 0, 1])))
    bonus = list()
    if "studio" in defs:  # editor model
        studio = defs["studio"]
        out.append(f'<!-- TODO: convert {studio} to .obj -->')
        bonus.append(f'model="{studio}"')
    elif dossier["type"] == "point":
        bonus.append('box="-8 -8 -8 8 8 8"')
    out.append(" ".join([head, color, *bonus]) + ">")
    if dossier["spec"] is not None:  # source based
        out.append(dossier["spec"].description.replace("&", "and"))
        fgd_keys = [p for p in dossier["spec"].properties if p.name not in dossier["old"]]
        spawnflags = dossier["spec"].spawnflags
    else:  # dummy spec
        fgd_keys = list()
        spawnflags = list()
    out.append("----- KEYS -----")
    for key in fgd_keys:
        if key.value_type == "choices":
            key_type, choice_list = xml_choices(key)
            choice_types.add(choice_list)
        else:
            key_type = key_types.get(key.value_type, "string")
        out.append(" ".join([f'<{key_type} key="{key.name}" name="{key.display_name}"',
                             f'value="{key.default_value}">{key.description}</{key_type}>']))
    for key_name in dossier["new"]:  # ur_keys
        key_type = guess_key_type(key_name, dossier["ur"][key_name])
        out.append(f'<{key_type} key="{key_name}" name="{key_name}">New in Titanfall; TODO: identify use</{key_type}>')
    # spawnflags
    if len(spawnflags) > 0:
        out.append("----- SPAWNFLAGS -----")
        out.extend(xml_spawnflags(spawnflags))
    out.append("----- NOTES -----")
    out.append(f"Introduced by {dossier['origin']}")
    if dossier["origin"] == "Source":
        # TODO: find a ratio at which you can safely say: "total refactor"
        out.extend([f"Added: {', '.join(dossier['new'])}",
                    f"Removed: {', '.join(dossier['old'])}",
                    "TODO: speculate on changes"])
    out.append(f'</{dossier["type"]}>')
    return "\n".join(out), choice_types
