from typing import Any, Dict, Set


def camelCase(snake_case: str) -> str:
    out = list()
    for word in snake_case.split("_"):
        out.append(word[0].upper() + word[1:].lower())
    out = "".join(out)
    return out[0].lower() + out[1:]


def ent_color(fgd, ent_schema: Dict[str, Any]):
    defs = {d["name"]: d["args"] for d in ent_schema["definitions"]}
    if "color" in defs:  # found
        return " ".join([f"{x / 255:.2f}" for x in defs["color"]["args"][0].split()])
    for base_ent_name in defs.get("base", list())[::-1]:  # last override first
        base_ent = fgd.entity_by_name(base_ent_name)
        color = ent_color(base_ent)  # recurse
        if color is not None:
            return color
    return None  # default


def ent_model(fgd, ent_schema: Dict[str, Any]):
    """trace BaseClass 'studio("ref.mdl")'"""
    defs = {d["name"]: d["args"] for d in ent_schema["definitions"]}
    if "studio" in defs:  # found
        return defs["studio"]["args"][0]
    for base_ent_name in defs.get("base", list())[::-1]:  # last override first
        base_ent = fgd.entity_by_name(base_ent_name)
        studio = ent_color(base_ent)  # recurse
        if studio is not None:
            return studio
    return None  # default


def fgd_point_ent_schema_to_xml(fgd, ent_name: str, r1_dd: Dict[str, Set[str]]) -> str:
    out = list()
    ent_schema = fgd.entity_by_name("ent_name").schema
    assert ent_schema["class_type"] == "PointClass"
    # TODO: diff keys (properties) against r1_keys
    # -- same type
    # -- TODOs for new keys (or prefill string type)
    ent_keys = {d["name"] for d in ent_schema["properties"]}
    r1_keys = set(r1_dd.keys())
    new_keys = r1_keys.difference(ent_keys)
    if len(new_keys) > 0:
        out.append(f"<!-- TODO: {', '.join(new_keys)} -->")
    ent_keys = ent_keys.difference(r1_keys)
    color = ent_color(ent_schema)
    color = "1 0 1" if color is None else color
    box = "-8 -8 -8 8 8 8"
    model = ent_model(ent_schema)
    if model is not None:
        out.append(f"<!-- TODO: {model=} -->")
        # TODO: rescale box to model
    out.append(f'<point name="{ent_name}" color="{color}" box="{box}">')
    out.append(ent_schema["description"].replace("&", "and"))
    out.append("----- KEYS -----")
    for key_name in ent_keys:
        key = ent_schema["properties"][key_name]
        key_d_name = key["display_name"]
        if key_name == "id":
            continue
        key_default = key["default_falue"]
        key_default = f' value="{key_default}"' if key_default != "" else ""
        key_desc = key["description"].replace("&", "and")
        # TODO: key_type & confirm r1_dd type matches
        out.append(f'<{key_type} key="{key_name}" name="{key_d_name}"{key_default}>{key_desc}</{type}>')
        # TODO: value if default exists
        if "choices" in key:
            # choices -> list
            choice = [f"<!-- {ent_name} -->",
                      f'<list name="{camelCase(key_d_name)}">',
                      *[f'''  <item name="{c['name']}" value="{c['value']}"/>''' for c in key["choices"]],
                      "</list>"]
            out.insert(0, "\n".join(choice) + "\n\n")
    # spawnflags
    if "spawnflags" in ent_schema:
        out.append("----- SPAWNFLAGS -----")
        for flag in ent_schema["spawnflags"]:
            flag_name = "FLAG_{flag['value']}"
            # NOTE: any multi-bit flag will break here, which is fine by me
            log2 = {2**i: i for i in range(32)}
            flag_bit = log2[flag["value"]]
            flag_default = flag["default_value"]
            flag_default = 0 if flag_default == "" else int(flag_default)
            flag_desc = flag["display_name"].replace("&", "and")
            out.append(f'<flag name="{flag_name}" bit="{flag_bit}" value="{flag_default}">{flag_desc}</flag>')
    out.append("----- NOTES -----")
    out.append("Inherited from Source")
    # TODO: verify XML (use Notepad++ XMLTools plugin)
    return "\n".join(out)


if __name__ == "__main__":
    import collections
    import fnmatch
    import functools
    import os

    import bsp_tool
    import valvefgd

    # TODO: switch paths depending on uname
    # cache all maps; uses a lot of RAM!
    r1md = "/media/bikkie/3964-3935/Mod/Titanfall/maps"
    r1m = {m[:-4]: bsp_tool.load_bsp(os.path.join(r1md, m)) for m in fnmatch.filter(os.listdir(r1md), "*.bsp")}
    r1omd = "/media/bikkie/3964-3935/Mod/TitanfallOnline/maps"
    r1om = {m[:-4]: bsp_tool.load_bsp(os.path.join(r1omd, m)) for m in fnmatch.filter(os.listdir(r1omd), "*.bsp")}
    maps = {**{f"r1/{m}": b for m, b in r1m.items()}, **{f"r1o/{m}": b for m, b in r1om.items()}}
    del r1m, r1om

    fgd = valvefgd.FgdParse("/home/bikkie/Documents/Code/GitHub/QtPyHammer/Team Fortress 2/bin/base.fgd")

    ent_file = open("out.ent", "w")

    for ent in fgd.entities:
        ent_name = ent["name"]
        # similar to fgd_gen_files/findings.txt
        r1_ent_instances = [e for b in r1m.values() for e in sum(b.search_all_entities(classname=ent_name).values())]
        r1_ent_keys = functools.reduce(lambda a, b: a.union(b), [set(e.keys()) for e in r1_ent_instances])
        r1_ent_dd = collections.defaultdict(set)
        for key in r1_ent_keys:
            if key in ("classname", "origin", "angles"):
                continue  # we know what those do
            for instance in r1_ent_instances:
                r1_ent_dd[key].add(instance.get(key, ""))  # sample every key
        if ent.schema["class_type"] == "PointClass":
            xml_snippet = fgd_point_ent_schema_to_xml(fgd, ent_name, dict(r1_ent_dd))
            ent_file.write(xml_snippet)
        del r1_ent_instances

    ent_file.close()
