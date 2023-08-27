# https://github.khronos.org/glTF-Tutorials/gltfTutorial/gltfTutorial_003_MinimalGltfFile.html
# https://github.khronos.org/glTF-Validator/
import json
import struct

import bsp_tool


# TODO: uvs
# TODO: materials
# TODO: each mesh as a scene object


def bsp_to_gltf(bsp: bsp_tool.Bsp):
    buffer = list()
    worldspawn = bsp.MODELS[0]
    for i in range(worldspawn.num_meshes):
        print(f"{i + 1:04d}/{worldspawn.num_meshes}")
        # NOTE: if going mesh by mesh, MeshBounds can't be used for min-max due to rotation!
        for vertex in bsp.vertices_of_model(0):
            position = bsp.VERTICES[vertex.position_index]
            # uv = vertex.albedo_uv
            # normal = bsp.VERTEX_NORMALS[vertex.normal_index]
            buffer.append(struct.pack("3f", *position))

    num_vertices = len(buffer)
    buffer = b"".join(buffer)
    buffer_filename = f"{bsp.filename}.bin"

    # write .gltf
    gltf = {"scene": 0, "scenes": [{"nodes": [0]}], "nodes": [{"mesh": 0}],
            "meshes": [{"primitives": [{"attributes": {"POSITION": 0}}]}],
            "buffers": [{"uri": buffer_filename, "byteLength": len(buffer)}],
            "bufferViews": [{"buffer": 0, "byteOffset": 0, "byteLength": len(buffer), "target": 34962}],
            "accessors": [{"bufferView": 0, "byteOffset": 0, "componentType": 5126, "type": "VEC3",
                           "count": num_vertices, "min": [-32768] * 3, "max": [32768] * 3}],
            "asset": {"version": "2.0"}}
    with open(f"{bsp.filename}.gltf", "w") as gltf_file:
        json.dump(gltf, gltf_file, indent=2)

    # write .bin
    with open(buffer_filename, "wb") as bin_file:
        bin_file.write(buffer)


if __name__ == "__main__":
    import sys
    if len(sys.argv) == 1:
        print("Usage: gltf.py MAP_FILENAME ...")
        sys.exit()
    for map_path in sys.argv[1:]:
        bsp = bsp_tool.load_bsp(map_path)
        print("generating {bsp.filename}.gltf")
        bsp_to_gltf(bsp)
