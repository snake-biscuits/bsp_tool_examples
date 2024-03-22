import os
import time

import bsp_tool
from bsp_tool.extensions import lightmaps
from bsp_tool.extensions.geometry import usd
from bsp_tool.utils import geometry
from bsp_tool.utils.vector import vec2


def printt(*args, **kwargs):
    print(f"[{time.strftime('%H:%M')}]", *args, **kwargs)


printt("Importing bsp...")
# game, md = "css", "D:/SteamLibrary/steamapps/common/counter-strike source/cstrike/maps/"
game, md = "cso2_2017", "E:/Mod/CSO2/organnerx/2017/"
# game, md = "cso2_2018", "E:/Mod/CSO2/organnerx/2018/"  # use cso2_2018 & split 4 lightmap groups
bsp = bsp_tool.load_bsp(os.path.join(md, "de_inferno.bsp"))

# lightmap pages to file
printt("Creating lightmap pages...")
collection = lightmaps.source.face_lightmaps(bsp)
coll_hdr = collection.subset("HDR.*")
page = lightmaps.LightmapPage.from_collection(coll_hdr)
page.save_as(f"{collection.name}.HDR", extension="tga")

# face meshes
printt("Extracting bsp meshes...")
meshes = [
    bsp.face_mesh(i) if face.displacement_info == -1 else bsp.displacement_mesh(i)
    for i, face in enumerate(bsp.FACES)]

# remap lightmap_uvs
printt("Remapping lightmap uvs...")
page_width, page_height = page.min_width, page.min_height
for (hdr, face_index), allocated_space in page.allocated_spaces.items():
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
worldspawn = bsp.MODELS[0]
worldspawn_meshes = [  # only faces with lightmaps
    mesh
    for i, mesh in enumerate(meshes[:worldspawn.num_faces])
    if bsp.FACES[i].lightmap.size.x != 0]
models = {
    "worldspawn": geometry.Model(worldspawn_meshes)}
# TODO: other models + entities (model.origin etc.)

# export mesh
printt("Writing .usda file...")
usd.USDA(models).save_as(f"{game}_{collection.name}.usda")

printt("Done!")
