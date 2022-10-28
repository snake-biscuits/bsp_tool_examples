import fnmatch
import os
import shutil

import bsp_tool
from bsp_tool.extensions import diff


s3 = "E:/Mod/ApexLegends/season3_3dec19/maps"
s4 = "E:/Mod/ApexLegends/season4/maps"
launch_depot = "depot/r5launch/game/r2/maps"
staging_depot = "depot/r5launch/game/r2/maps"

s3_maps = set(fnmatch.filter(os.listdir(s3_3dec19), "*.bsp"))
s4_maps = set(fnmatch.filter(os.listdir(s4), "*.bsp"))

common_map_names = sorted(s4_maps.union(s3_maps))

for map_name in common_map_names:
    print(f"*** {map_name} ***")
    s3_bsp = bsp_tool.load_bsp(os.path.join(s3, map_name))
    s4_bsp = bsp_tool.load_bsp(os.path.join(s4, map_name))
    diff.diff_rbsps(s3_bsp, s4_bsp)
    print("\n\n")
    
    for bsp, log_dir in zip((s3_bsp, s4_bsp), ("s3_logs", "s4_logs")):
        if hasattr(bsp, "PAKFILE"):
            logs = fnmatch.filter(bsp.PAKFILE.namelist(), "*.txt")
            for log_file in logs:
                print(f"Extracting {log_file} from {bsp.filename} ...")
                bsp.PAKFILE.extract(log_file, path=log_dir)
                ext_filename = os.path.join(log_dir, log_file)
                ext_dir, ext_file = os.path.split(ext_filename)
                new_filename = os.path.join(ext_dir, f"{map_dir.replace('/', '.')}.{ext_file}")
                shutil.move(ext_filename, new_filename)
                print(f"\-> Renamed to {new_filename}")
