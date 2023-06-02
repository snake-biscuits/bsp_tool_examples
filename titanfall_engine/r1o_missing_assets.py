from collections import defaultdict
import fnmatch
import os
import re
import sys
sys.path.append("../bsp_tool")
import bsp_tool  # noqa E402


# https://developer.valvesoftware.com/wiki/Category:List_of_Shader_Parameters
# NOTE: some of the params ending in 2 are new to titanfall _bm materials
# TODO: check to see if we missed any
vmt_params = ("basetexture", "basetexture2", "blendmodulatetexture", "bumpmap", "bumpmap2",
              "detail", "detail2", "detailnormal", "detailnormal2",
              "envmapmask", "phongexponenttexture",
              "reflectiontint", "reflectiontint2", "reflectiontintshiniess", "reflectiontintshininess2",
              "shininess", "shininess2")
vtf_patterns = {re.compile(f'\\s"${p}"\\s"(.*)"') for p in vmt_params}

assets_dir = "E:/Mod/TitanfallOnline/TitanFallOnline/assets_dump"
materials_dir = os.path.join(assets_dir, "materials")

missing = defaultdict(set)
# ^ {"mp_mapname.bsp": {"folder/asset.ext"}}
for md in ("E:/Mod/Titanfall/maps", "E:/Mod/TitanfallOnline/maps"):
    for map_name in fnmatch.filter(os.listdir(md), "*.bsp"):
        bsp = bsp_tool.load_bsp(os.path.join(md, map_name))
        for td in bsp.TEXTURE_DATA:
            vertex_type = (td.flags & bsp_tool.branches.respawn.titanfall.MeshFlags.MASK_VERTEX).name
            vmt_name = bsp.TEXTURE_DATA_STRING_DATA[td.name_index]
            vmt_path = f"{materials_dir}/{vmt_name}.vmt"
            if not os.path.exists(vmt_path):
                missing[map_name[:-4]].add(f"materials/{vmt_name.lower()}")
                continue
            # check vtfs
            with open(mat_path, "r") as vmt_file:
                for line in vmt_file:
                    for pattern in vtf_patterns:
                    match = pattern.match(line)
                    if match is not None:
                        vtf_name = match.groups()[0]
                        vtf_path = f"{materials_dir}/{vtf_name}.vmt"
                        if not os.path.exists(vtf_path):
                            missing[map_name[:-4]].add(f"materials/{vtf_name.lower()}")
        if not hasattr(bsp, "GAME_LUMP"):
            continue
        for mdl_name in bsp.GAME_LUMP.sprp.model_names:
            mdl_path = os.path.join(assets_dir, mdl_name)
            if not os.path.exists(mdl_path):
                missing[map_name[:-4]].add(vtf_name.lower())
        # TODO: dynamic models, particles, sounds
            


for map_name in sorted(missing):
    print(map_name)
    for filename in sorted(missing[map_name]):
        print(f"  {filename}")