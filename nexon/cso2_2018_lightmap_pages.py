import time

import bsp_tool
from bsp_tool.extensions import lightmaps
from bsp_tool.extensions.geometry import usd
from bsp_tool.utils import geometry
from bsp_tool.utils.vector import vec2


def printt(*args, **kwargs):
    print(f"[{time.strftime('%H:%M')}]", *args, **kwargs)


printt("Importing bsp...")
bsp = bsp_tool.load_bsp("/media/bikkie/3964-39352/Mod/CSO2/organnerx/2018/de_inferno.bsp")
# NOTE: de_inferno needed some manual cleanup of duplicate material names
# -- took around 10 mins to convert on Lenovo Ideapad 110S (2 GB RAM, 2.48 GHz CPU)
# -- 8 of those 10 mins was lightmap extraction

# lightmap pages to file
printt("Creating lightmap pages...")
collection = lightmaps.cso2_2018.face_lightmaps(bsp)
coll_a = collection.subset("HDR.A.*")
coll_b = collection.subset("HDR.B.*")
coll_c = collection.subset("HDR.C.*")
coll_d = collection.subset("HDR.D.*")

page = lightmaps.LightmapPage.from_collection(coll_a)
page.save_as(f"{collection.name}.HDR.A", extension="tga")

for fn in coll_b.namelist():
    page.collection[fn.replace(".B.", ".A.")] = coll_b[fn]
page.save_as(f"{collection.name}.HDR.B", extension="tga")

for fn in coll_c.namelist():
    page.collection[fn.replace(".C.", ".A.")] = coll_c[fn]
page.save_as(f"{collection.name}.HDR.C", extension="tga")

for fn in coll_d.namelist():
    page.collection[fn.replace(".D.", ".A.")] = coll_d[fn]
page.save_as(f"{collection.name}.HDR.D", extension="tga")

# face meshes
printt("Extracting bsp meshes...")
meshes = [
    bsp.face_mesh(i) if face.displacement_info == -1 else bsp.displacement_mesh(i)
    for i, face in enumerate(bsp.FACES)]

# remap lightmap_uvs
printt("Remapping lightmap uvs...")
page_width, page_height = page.min_width, page.min_height
for (hdr, a, face_index), allocated_space in page.allocated_spaces.items():
    mesh = meshes[face_index]
    scale = vec2(
        allocated_space.width / page_width,
        allocated_space.height / page_height)
    offset = vec2(
        allocated_space.x / page_width,
        allocated_space.y / page_height)
    for i, polygon in enumerate(mesh.polygons):
        for j, vertex in enumerate(polygon.vertices):
            page_uv1 = vec2(
                vertex.uv[1].x * scale.x + offset.x,
                vertex.uv[1].y * scale.y + offset.y)
            page_uv1.y = 1 - page_uv1.y  # invert
            mesh.polygons[i].vertices[j].uv[1] = page_uv1

# grouping models
printt("Creating models...")
# TODO: exclude faces w/ no lightmaps
models = {
    "worldspawn": geometry.Model(meshes[:bsp.MODELS[0].num_faces])}
# TODO: group other models & get their origins from entities

# export mesh
printt("Writing .usda file...")
usd.USDA(models).save_as(f"cso2_2018_{collection.name}.usda")

printt("Done!")
