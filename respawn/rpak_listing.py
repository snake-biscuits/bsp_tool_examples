from collections import defaultdict
import fnmatch
import json
import os

import bsp_tool


# get material names we want from maps
md = "E:/Mod/Titanfall2/maps"  # maps extracted from .vpks
map_matls = {m[:-4]: bsp_tool.load_bsp(os.path.join(md, m)).TEXTURE_DATA_STRING_DATA
             for m in fnmatch.filter(os.listdir(md), "*.bsp")}
map_matls = {m: list(map(str.lower, tdsd)) for m, tdsd in map_matls.items()}
all_matls = {x for ml in map_matls.values() for x in ml}
print(f"got material list from maps ({len(all_matls)} materials)")

# check rpak lists (in Legion+ export dir)
rld = "E:/Mod/_tools/Source Engine - Respawn/Legion+1.7.0/exported_files/lists"
log = defaultdict(set)
lists = os.listdir(rld)
for i, list_filename in enumerate(lists):
    rpak_name = list_filename.split(".")[0]
    print(f"{i + 1:03d} / {len(lists)} | {rpak_name}")
    with open(os.path.join(rld, list_filename)) as list_file:
        for matl_name in list_file:
            matl_name = matl_name.rstrip("\r\n")  # LegionPlus lists have CRLF line endings
            if matl_name in all_matls:
                log[rpak_name].add(matl_name.replace("\\", "/"))

# ranking = {k: len(v) for k, v in log.items()}
# {print(f"{k:<24} {str(ranking[k]):>16}") for k in sorted(ranking, key=lambda k: -ranking[k])}

log = {rn: sorted(mns) for rn, mns in log.items()}
with open("rpak_map_materials.json", "w") as json_file:
    json.dump(log, json_file, indent=2)
