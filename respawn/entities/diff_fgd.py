import collections
import fnmatch
import os
from typing import Dict, Set

import bsp_tool
import valvefgd


# r1md = "/media/bikkie/3964-3935/Mod/Titanfall/maps"
r1md = "E:/Mod/Titanfall/maps"
r1m = {m[:-4]: bsp_tool.load_bsp(os.path.join(r1md, m)) for m in fnmatch.filter(os.listdir(r1md), "*.bsp")}


def ent_def(**filters: Dict[str, str]) -> Dict[str, Set[str]]:
    out = collections.defaultdict(set)
    for bsp in r1m.values():
        for entity in sum(bsp.search_all_entities(**filters).values(), start=list()):
            for key, value in entity.items():
                if key in ("classname", "spawnflags"):
                    continue
                out[key].add(value)
    return dict(out)


def ent_diff(fgd: valvefgd.Fgd, ent_name: str) -> str:
    ent_values = ent_def(classname=ent_name)
    ent_keys = set(ent_values.keys())
    # Titanfall only
    if ent_name not in [e.name for e in fgd.entities]:
        if list(ent_values.get("model", {""}))[0].startswith("*"):
            ent_keys.remove("model")
        return "New in Titanfall\nKeys: " + ", ".join(sorted(ent_keys))
    # Source based
    fgd_ent = fgd.entity_by_name(ent_name)
    fgd_keys = {p.name for p in fgd_ent.properties}
    # remove keys inherent to type
    if fgd_ent.class_type == "PointClass" and "origin" in ent_keys:
        ent_keys.remove("origin")
    if fgd_ent.class_type == "SolidClass" and "model" in ent_keys:
        ent_keys.remove("model")
    # breakdown
    out = ["Inherited from Source"]
    new_keys = ent_keys.difference(fgd_keys)
    if len(new_keys) > 0:
        out.append("New: " + ", ".join(sorted(new_keys)))
    old_keys = fgd_keys.difference(ent_keys)
    if len(old_keys) > 0:
        out.append("Removed: " + ", ".join(sorted(old_keys)))
    return "\n".join(out)


if __name__ == "__main__":
    # base_fgd = valvefgd.FgdParse("/media/bikkie/3964-3935/Mod/Portal2/bin/base.fgd")
    base_fgd = valvefgd.FgdParse("D:/SteamLibrary/steamapps/common/Portal/bin/base.fgd")
    all_classnames = collections.defaultdict(set)
    for bsp in r1m.values():
        for block in ["ENTITIES", *[f"ENTITIES_{x}" for x in ("env", "fx", "script", "spawn", "snd")]]:
            for e in getattr(bsp, block):
                all_classnames[block].add(e["classname"])
    for block in sorted(all_classnames):
        print("***", block, "***")
        for classname in sorted(all_classnames[block]):
            print(f"{classname}:", ent_diff(base_fgd, classname), sep="\n", end="\n\n")
