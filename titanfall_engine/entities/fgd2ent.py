"""superceded by MRVN-Radiant/MRVN-Entities"""
import collections
import fnmatch
import functools
import os
# import re
from typing import Any, Dict, List, Set, Union

import sys  # noqa
import bsp_tool  # noqa
import valvefgd  # noqa


MapDict = Dict[str, bsp_tool.base.Bsp]
Entity = Dict[str, str]
# ^ {"key": "value"}
OmegaEntity = Dict[str, List[str]]
# ^ {"key": ["value1", "value2"]}


def ur_ent(maps: MapDict, classname: str = None, **filters: Entity) -> OmegaEntity:
    """Find 'ur' entity (all keys & values used in official maps)"""
    # NOTE: will get a handful of false positives from renamed ents w/ forgotten key values
    if classname is not None:
        filters["classname"] = classname
    assert "classname" in filters
    out = collections.defaultdict(set)
    for map_name in maps:
        bsp = maps[map_name]
        for ent in sum(bsp.search_all_entities(**filters).values(), start=list()):
            for key, value in ent.items():
                out[key].add(value)
    return {k: sorted(out[k]) for k in sorted(out)}


Dossier = Dict[str, Union[str, OmegaEntity]]

class_types = dict(PointClass="point", KeyFrameClass="point", MoveClass="point",
                   SolidClass="group")


def id_ent(omega_entity: OmegaEntity, fgd: valvefgd.Fgd) -> Dossier:
    # TODO: pass in origin names for omega_entity & fgd
    # TODO: force fgd_entity classname to compare
    classname = omega_entity["classname"][0]
    omega_keys = set(omega_entity.keys())
    out = {"classname": classname, "ur": omega_entity, "type": "point", "spec": None,
           "old": set(), "shared": set(), "new": omega_keys}
    if classname not in [e.name for e in fgd.entities]:
        out["origin"] = "Titanfall"
        if any([v.startswith("*") for v in omega_entity.get("model", list())]):  # brush entity
            out["new"].remove("model")
            out["type"] = "group"
        if "origin" in out["new"]:  # automatically added by Radiant
            out["new"].remove("origin")
        return out
    # TODO: catch editorclass / spawnclass subtype
    fgd_entity = fgd.entity_by_name(classname)
    fgd_keys = {p.name for p in fgd_entity.properties}
    out.update({"origin": "Source",
                "type": class_types[fgd_entity.class_type],
                "new": omega_keys.difference({*fgd_keys, "origin"}),
                "shared": omega_keys.intersection({*fgd_keys, "origin"}),
                "old": fgd_keys.difference({*omega_keys, "origin"}),
                "spec": fgd_entity})
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
        out.append(f'  <item name="{choice.display_name}" value="{choice.value}"/>')
    out.append("</list>\n")
    return type_name, "\n".join(out)


log2 = {2 ** i: i for i in range(32)}  # for spawnflags conversion


def xml_spawnflags(spawnflags: List[valvefgd.FgdEntitySpawnflag]) -> str:
    out = list()
    for flag in spawnflags:
        # flag.display_name, value, default_value
        name = "_".join(["FLAG", *map(str.upper, flag.display_name.split())])
        bit = log2[flag.value]
        default = int(flag.default_value)
        # TODO: check for split points that could be descs (",.-" etc.)
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
                    out[d["name"]] = d["args"]
    return out


key_types = {"float": "real", "boolean": "boolean", "integer": "integer", "studio": "model",
             "sound": "sound", "target_source": "targetname", "target_dest": "targetname",
             "angle": "angles"}
# ^ {"fgd_key": "key_type"}


def guess_key_type(key_name: str, key_values: Set[str]) -> str:
    """ur_key key_type"""
    # TODO: sound (need radiant to index soundscripts like source)
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
    # TODO: tag paths for TODOs (might be material)
    if "target" in key_name.lower():  # TEST: false positives
        return "targetname"
    if "angles" in key_name.lower():  # TEST: false positives
        return "angles"
    return "string"


def sanitise_desc(desc: str) -> str:
    out = desc
    subs = {". ": ".\n", "&": "&amp;", "<": "&lt;", ">": "&gt;"}
    for old, new in subs.items():
        out = out.replace(old, new)
    return out


common_keys = {"targetname": ("Name", "The name that other entities refer to this entity by."),
               "model": ("World Model", ""),
               "angles": ("Pitch Yaw Roll (Y Z X)", "This entity's orientation in the world.\n"
                          "Pitch is rotation around the Y axis, Yaw is the rotation around the Z axis, Roll is the rotation around the X axis.")}  # noqa
# ^ similar to guess_key_type, but for descriptions


def xml_ent(dossier: Dossier) -> (str, Set[str]):
    out = list()
    choice_types = set()
    defs = ent_definitions(dossier["spec"]) if dossier["spec"] is not None else dict()
    head = f'<{dossier["type"]} name=\"{dossier["classname"]}\"'
    color = " ".join(map(str, defs.get("color", [1, 0, 1])))
    bonus = list()
    if "studio" in defs:  # editor model
        studio = defs["studio"][0]
        out.append(f'<!-- TODO: convert {studio} to .obj -->')
        bonus.append(f'model="{studio}"')
    elif dossier["type"] == "point":
        bonus.append('box="-8 -8 -8 8 8 8"')
    out.append(" ".join([head, f'color="{color}"', *bonus]) + ">")
    if dossier["spec"] is not None:  # source based
        out.append(sanitise_desc(dossier["spec"].description))
        fgd_keys = [p for p in dossier["spec"].properties if p.name not in dossier["old"]]
        spawnflags = dossier["spec"].spawnflags
    else:  # dummy spec
        fgd_keys = list()
        spawnflags = list()
    out.append("----- KEYS -----")
    for key in fgd_keys:
        if key.value_type == "choices":
            # choices_dict = {c.display_name.lower(): c.value for c in key.choices}
            if {c.display_name.lower(): c.value for c in key.choices} == {"no": 0, "yes": 1}:
                key_type = "boolean"  # ridiculous edge case
            else:
                key_type, choice_list = xml_choices(key)
                choice_types.add(choice_list)
        else:
            key_type = key_types.get(key.value_type, "string")
        key_description = "" if key.description is None else key.description
        key_description = sanitise_desc(key_description)
        out.append(" ".join([f'<{key_type} key="{key.name}" name="{key.display_name}"',
                             f'value="{key.default_value}">{key_description}</{key_type}>']))
    omega_keys = {k for k in dossier["new"] if k not in ("classname",)}
    for key_name in omega_keys:
        # NOTE: will get a handful of false positives from renamed ents w/ forgotten key values
        if key_name != "spawnflags":
            key_type = guess_key_type(key_name, dossier["ur"][key_name])
            key_display_name, key_desc = common_keys.get(key_name, (key_name, "New in Titanfall; TODO: identify"))
            out.append(f'<{key_type} key="{key_name}" name="{key_display_name}">{key_desc}</{key_type}>')
        else:  # identify new spawnflags
            omega_spawnflag = functools.reduce(lambda a, b: a | b, map(int, dossier["ur"]["spawnflags"]))
            used_flags = f"{omega_spawnflag:032b}"  # bits
            spawnflags = [valvefgd.FgdEntitySpawnflag(display_name=f"UNKNOWN_{i}", value=2**i, default_value=0)
                          for i in range(32) if used_flags[::-1][i] == "1"]  # sure hope this lines up
    if len(spawnflags) > 0:
        out.append("----- SPAWNFLAGS -----")
        out.extend(xml_spawnflags(spawnflags))
    out.append("----- NOTES -----")
    out.append(f"Introduced by {dossier['origin']}")
    if dossier["origin"] == "Source":
        if len(omega_keys) > 0:
            out.append(f"Added: {', '.join(omega_keys)}")
        old_keys = {*dossier["old"]}
        if len(old_keys) > 0:
            out.append(f"Removed: {', '.join(old_keys)}")
        if len(omega_keys) != 0 or len(old_keys) != 0:
            out.append("TODO: identify changes")
    # TODO: find a ratio at which you can safely say: "total refactor"
    out.append(f'</{dossier["type"]}>')
    return "\n".join(out), choice_types


def print_xml(maps: MapDict, fgd: valvefgd.Fgd, classname: str, **filters: Dict[str, str]):
    """One at a time"""
    ent_omega = ur_ent(maps, classname, **filters)
    ent_dossier = id_ent(ent_omega, fgd)
    ent_txt, choice_types_txt = xml_ent(ent_dossier)
    print


def batch(maps: MapDict, fgd: valvefgd.Fgd, classnames: List[Union[str, Dict]]):
    """Re-use choice types"""
    choice_types = collections.defaultdict(set)
    # ^ {'<list name="choice_type">...': {"classname", ...}}
    ents = list()
    for x in classnames:
        if isinstance(x, str):
            filters = dict(classname=x)
        elif isinstance(x, dict):
            filters = x
        ent_omega = ur_ent(maps, **filters)
        ent_dossier = id_ent(ent_omega, fgd)
        ent_txt, ent_choices = xml_ent(ent_dossier)
        ents.append(ent_txt)
        for ec in ent_choices:
            choice_types[ec].add(filters["classname"])
        # TODO: ensure list name of each ent_choice_list is unique
        # -- camelCase w/ entity_name
        # -- probably need to regex first line
    return choice_types, ents


if __name__ == "__main__":
    header = """<?xml version="1.0"?>
<!--
    Titanfall 2 entity definitions for MRVN-radiant
        Spawnpoint, hardpoint, ctf flag & zipline definitions by catornot (2022-11-2)
        Bounding Boxes and Models by snake-biscuits (2022-11-6)
        All other defintions by snake-biscuits (2022 November) [generated w/ bsp_tool_examples]
-->
<!-- TODO:
    Identify broken / unused / unimplemented keys
    Test if Titanfall can handle missing entity keys (some scripts might complain)
-->
<classes>
<!--
=============================================================================
 OPTION KEY TYPES
=============================================================================
-->\n"""

    footer = """</classes>"""

    print("loading maps...")
    # md = "/media/bikkie/3964-3935/Mod/Titanfall/maps"
    r1md = "E:/Mod/Titanfall/maps"
    r1m = {m[:-4]: bsp_tool.load_bsp(os.path.join(r1md, m)) for m in fnmatch.filter(os.listdir(r1md), "*.bsp")}
    r1omd = "E:/Mod/TitanfallOnline/maps"
    r1om = {m[:-4]: bsp_tool.load_bsp(os.path.join(r1omd, m)) for m in fnmatch.filter(os.listdir(r1omd), "*.bsp")}
    maps = {**{f"r1/{m}": b for m, b in r1m.items()}, **{f"r1o/{m}": b for m, b in r1om.items()}}
    # r2md = "E:/Mod/Titanfall2/maps"
    # r2m = {m[:-4]: bsp_tool.load_bsp(os.path.join(r2md, m)) for m in fnmatch.filter(os.listdir(r2md), "*.bsp")}
    # maps = r2m
    # r5_s3md = "E:/Mod/ApexLegends/season3/3dec19/maps"  # Christmas Mirage LTM
    # r5_s3m = {m[:-4]: bsp_tool.load_bsp(os.path.join(r5_s3md, m)) for m in fnmatch.filter(os.listdir(r5_s3md), "*.bsp")}
    # maps = r5_s3m
    print(len(maps), "maps loaded")

    print("loading fgd...")
    # fgd_path = "/media/bikkie/3964-3935/Mod/Portal2/bin/base.fgd"
    fgd_path = "D:/SteamLibrary/steamapps/common/Portal/bin/base.fgd"
    fgd = valvefgd.FgdParse(fgd_path)

    # all Titanfall Entity Lumps
    ent_blocks = ("ENTITIES", *(f"ENTITIES_{x}" for x in ("env", "fx", "script", "spawn", "snd")))

    print("gathering classnames...")
    all_classnames = collections.defaultdict(set)
    for bsp in maps.values():
        for block in ent_blocks:
            for entity in getattr(bsp, block):
                all_classnames[block].add(entity["classname"])
                # TODO: catch unique editorclasses

    for block in ent_blocks:
        print(len(all_classnames[block]), "classnames found in", block)

    for block in ent_blocks:
        print(f"batching {block}...")
        choice_types, ents = batch(maps, fgd, all_classnames[block])
        print(f"writing {block}.xml...")
        with open(f"fgd2ent_files/r1/{block}.xml", "w") as ent_file:
            ent_file.write(header + "\n")
            ent_file.write("\n\n".join([f"<!-- used by {', '.join(v)} -->\n{k}" for k, v in choice_types.items()]))
            ent_file.write("""\n<!--
=============================================================================
 ENTITIES IN ALPHABETICAL ORDER
=============================================================================
-->\n""")
            ent_file.write("\n\n".join(ents))
            ent_file.write("\n</classes>\n")
        print("Done!")
    print("Finished!")
