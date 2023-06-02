from collections import defaultdict
import fnmatch
import os
import re
import sys
sys.path.append("../bsp_tool")
import bsp_tool  # noqa E402


missing = set()
results = set()
for md in ("E:/Mod/Titanfall/maps", "E:/Mod/TitanfallOnline/maps"):
    print(f"> {md}")
    for map_name in fnmatch.filter(os.listdir(md), "*.bsp"):
        print(f">> {map_name}")
        bsp = bsp_tool.load_bsp(os.path.join(md, map_name))
        for td in bsp.TEXTURE_DATA:
            vertex_type = (td.flags & bsp_tool.branches.respawn.titanfall.MeshFlags.MASK_VERTEX).name
            mat_name = bsp.TEXTURE_DATA_STRING_DATA[td.name_index]
            mat_dir = "E:/Mod/TitanfallOnline/TitanFallOnline/assets_dump/materials"
            mat_path = f"{mat_dir}/{bsp.TEXTURE_DATA_STRING_DATA[td.name_index]}.vmt"
            if not os.path.exists(mat_path):
                missing.add(mat_name.lower())
                continue
            with open(mat_path, "r") as vmt_file:
                for line in vmt_file:
                    m = re.match(r'"(.*)"', line)  # shader
                    if m is not None:
                        shader = m.groups()[0]
                        results.add((vertex_type, shader))
                        continue

print("*** SKIPPED ***")
{print(m) for m in sorted(missing)}
print("-" * 35)
{print(f"{vertex_type:<16} {shader}") for vertex_type, shader in sorted(results)}
print("-" * 35)
print(f"failed to locate {len(missing)} .vmts")
