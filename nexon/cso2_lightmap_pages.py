import bsp_tool
from bsp_tool.extensions import lightmaps


bsp = bsp_tool.load_bsp("E:/Mod/CSO2/maps/de_dust2.bsp")
# bsp = bsp_tool.load_bsp("E:/Mod/CSO2/organnerx/2018/dm_killhouse.bsp")

# lightmap groups
collection = lightmaps.cso2.face_lightmaps(bsp)
a = collection.subset("HDR.A.*")
b = collection.subset("HDR.B.*")
c = collection.subset("HDR.C.*")
d = collection.subset("HDR.D.*")

# pack once
page = lightmaps.LightmapPage.from_collection(a)
page.save_as(f"{collection.name}.HDR.A", extension="tga")

for fn in b.namelist():
    page.collection[fn.replace("B", "A")] = b[fn]
page.save_as(f"{collection.name}.HDR.B", extension="tga")

for fn in c.namelist():
    page.collection[fn.replace("C", "A")] = c[fn]
page.save_as(f"{collection.name}.HDR.C", extension="tga")

for fn in d.namelist():
    page.collection[fn.replace(".D.", ".A.")] = d[fn]
assert len(page.collection) == len(a), "didn't replace images correctly"
page.save_as(f"{collection.name}.HDR.D", extension="tga")


# model = bsp.model(0)
# TODO: remap uvs to match page.child_bounds
# -- face_bounds = {int(k.split(".")[-1]): d for k, d in page.child_bounds().items()}
# -- assert len(model.meshes) == len(face_bounds)
# -- remap uv1 to face_bounds for each
# usd.USDA({"worldspawn": model}).save_as("{collection.name}.remapped_uv1.usda")
