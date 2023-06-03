from collections import defaultdict
import fnmatch
import os
import re

from bsp_tool.extensions import archives  # v0.5.0 / github@latest


r1_vpk_dir = "D:/SteamLibrary/steamapps/common/Titanfall/vpk"
r1o_dir = "E:/Mod/TitanfallOnline/TitanFallOnline/assets_dump"

missing = defaultdict(set)
# ^ {"vpk_name": {"folder/asset.ext"}}
for vpk_name in fnmatch.filter(os.listdir(r1_vpk_dir), "englishclient_*.pak000_dir.vpk"):
    vpk = archives.respawn.Vpk(vpk_name)
    vpk_name_short = re.match(r"englishclient_(.*).bsp.pak000_dir.vpk").groups()[0]
    for asset_path in vpk.namelist():
        if asset_path.startswith("depot"):
            continue
        if not os.path.exists(os.path.join(r1o_dir, asset_path)):
            missing[vpk_name_short].add(asset_path)


# TODO: compare crcs for assets duplicated across multiple vpks
# -- each map presumably mounts only common + their own vpk


# TODO: generate filelists for extraction
# -- find the least number of extractions nessecary
for vpk_name in sorted(missing):
    print(vpk_name)
    for asset_path in sorted(missing[vpk_name]):
        print(f"  {asset_path}")
