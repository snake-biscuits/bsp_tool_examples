import bsp_tool
from bsp_tool.extensions.convert.respawn import titanfall_to_titanfall2 as upgrade


# map_dir & out_dir
md = "E:/Mod/Titanfall/maps"
od = "D:/SteamLibrary/steamapps/common/Titanfall2/R2Northstar/mods/bikkie.r1ain/mod/maps"

# find r1 maps that aren't in r1o
# use os.listdir & fnmatch.filter if you don't have maplists typed up
r1m = {x.rstrip("\n") for x in open("E:/Mod/Titanfall/maplist.txt").readlines()}
r1om = {x.rstrip("\n") for x in open("E:/Mod/TitanfallOnline/maplist.txt").readlines()}
ml = sorted(r1m.difference(r1om | {"mp_lobby"}))

# maps = {m: bsp_tool.load_bsp(f"{md}/{m}.bsp") for m in ml}
# {print(f"{m:<24} {str(len(b.TRICOLL_TRIANGLES)):>12}") for m, b in maps.items()}

# for m in ml:
#     print(f"converting {m}")
#     bsp = bsp_tool.load_bsp(f"{md}/{m}.bsp")
#     upgrade(bsp, od)

# focus on colony, since it's the smallest map on the list
bsp = bsp_tool.load_bsp(f"{md}/mp_colony.bsp")
upgrade(bsp, od)
