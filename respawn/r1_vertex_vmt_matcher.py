# NOTE: path capitalisation may make things tricky on linux
import fnmatch
import os
import re

import bsp_tool


r1_materials = "E:/Mod/Titanfall/materials"
r1o_materials = "E:/Mod/TitanfallOnline/TitanFallOnline/assets_dump/materials"

shader_pattern = re.compile(r'([a-zA-Z_]+)|"([a-zA-Z_]+)"')

# search
results, missing = set(), set()
bad_parse = set()
for md in ("E:/Mod/Titanfall/maps", "E:/Mod/TitanfallOnline/maps"):
    print(f"> {md}")
    for map_name in fnmatch.filter(os.listdir(md), "*.bsp"):
        print(f">> {map_name}")
        bsp = bsp_tool.load_bsp(os.path.join(md, map_name))
        for td in bsp.TEXTURE_DATA:
            vertex_type = (td.flags & bsp_tool.branches.respawn.titanfall.MeshFlags.MASK_VERTEX).name
            vmt_name = bsp.TEXTURE_DATA_STRING_DATA[td.name_index].lower()
            vmt_path = f"{bsp.TEXTURE_DATA_STRING_DATA[td.name_index]}.vmt"
            if not os.path.exists(os.path.join(r1_materials, vmt_path)):
                if not os.path.exists(os.path.join(r1o_materials, vmt_path)):
                    missing.add(vmt_name)
                    continue
                else:
                    vmt_path = os.path.join(r1o_materials, vmt_path)
            else:
                vmt_path = os.path.join(r1_materials, vmt_path)
            with open(vmt_path, "r") as vmt_file:
                matches = {shader_pattern.match(line) for line in vmt_file}
                if matches == {None}:
                    bad_parse.add(vmt_name)
                else:
                    assert len(matches) == 2, f"{vmt_name}: {matches}"
                    shader = [g for g in list(matches.difference({None}))[0].groups() if g is not None][0]
                    assert shader is not None, f"{vmt_name}: {matches}"
                    results.add((vertex_type, shader))
                    # if shader == "Water":  # "VertexLitGeneric"
                    #     print(f"{vertex_type:<16} {vmt_name}")


# report
if len(missing) > 0:
    print("*** NOT FOUND ***")
    {print(m) for m in sorted(missing)}
if len(bad_parse) > 0:
    print("*** BAD PARSE ***")
    {print(m) for m in sorted(bad_parse)}
print("-" * 35)
{print(f"{vertex_type:<16} {shader}") for vertex_type, shader in sorted(results)}
print("-" * 35)
print(f"failed to locate {len(missing)} .vmts")
print(f"failed to parse {len(bad_parse)} .vmts")
