#include <cstdio>
#include <cstring>

#include "gltf.hpp"


// TODO: C++20 std::format & RapidJSON for .gltf component


typedef struct {
    Vertex   position;          // float          VEC3  POSITION
    Vertex   normal;            // float          VEC3  NORMAL
    float    uv[2];             // float          VEC2  TEXCOORD_0
    uint8_t  colour[4];         // unsigned byte  VEC4  COLOR_0
    float    lightmap_uv[2];    // float          VEC2  TEXCOORD_1
    float    lightmap_step[2];  // float          VEC2  TEXCOORD_2
    // theory: lightmap_step is added to lightmap uv (increments style)
    // TODO: int32_t  tangent[2];  => float  tangent[4]  (float VEC4 TANGENT)
} VertexGLTF;


// TODO: base json for bufferView
// span { start, length } -> { bufferOffset, byteLength }
// need some struct / class to carry json metadata per mesh
// MaterialSort.{lightmap,cubemap}_index

// TODO: lightmaps -> .png (different materials & textures across r1 & r2)
// SKY_A_0, ..._B_0, ..._1, etc.
// RTL_A_0, ..._B_0, ..._1, etc.


int main(int argc, char* argv[]) {
    if (argc == 1) { printf("Usage: %s [FILENAME] ...\n", argv[0]); }
    for (int i = 1; i < argc; i++) {
        char*  filename = argv[i];
        printf("converting %s ...\n", filename);

        // load bsp data
        RespawnBsp  bsp(filename);
        if (!bsp.is_valid()) {
            fprintf(stderr, "%s is not a Titanfall / Titanfall 2 .bsp!\n", filename);
            continue;
        }
        #define GET_LUMP(T, n, i)  std::vector<T>  n;  bsp.load_lump<T>(i, n)
        GET_LUMP(Vertex,         VERTICES,         0x03);
        GET_LUMP(Model,          MODELS,           0x0E);
        GET_LUMP(Vertex,         VERTEX_NORMALS,   0x1E);
        GET_LUMP(uint16_t,       MESH_INDICES,     0x4F);
        GET_LUMP(Mesh,           MESHES,           0x50);
        GET_LUMP(MaterialSort,   MATERIAL_SORTS,   0x52);
        GET_LUMP(VertexUnlit,    VERTEX_UNLIT,     0x47);
        GET_LUMP(VertexLitFlat,  VERTEX_LIT_FLAT,  0x48);
        GET_LUMP(VertexLitBump,  VERTEX_LIT_BUMP,  0x49);
        GET_LUMP(VertexUnlitTS,  VERTEX_UNLIT_TS,  0x4A);
        #undef GET_LUMP
        bsp.file.close();

        // generate .bin buffer(s)
        std::vector<VertexGLTF>  vertex_buffer;
        std::vector<uint32_t>    index_buffer;
        // vertex buffer
        VertexGLTF gltf_vertex;
        // TODO: VEC4 tangent & maybe lightmap step
        for (const auto &bsp_vertex : VERTEX_UNLIT) {
           gltf_vertex.position = VERTICES[bsp_vertex.position_index];
           gltf_vertex.normal   = VERTEX_NORMALS[bsp_vertex.normal_index];
           memcpy(gltf_vertex.uv,     bsp_vertex.uv,     sizeof(float)   * 2);
           memcpy(gltf_vertex.colour, bsp_vertex.colour, sizeof(uint8_t) * 4);
           memset(gltf_vertex.lightmap_uv, 0, sizeof(float) * 2);
           vertex_buffer.emplace_back(gltf_vertex);
        }
        for (const auto &bsp_vertex : VERTEX_LIT_FLAT) {
           gltf_vertex.position = VERTICES[bsp_vertex.position_index];
           gltf_vertex.normal   = VERTEX_NORMALS[bsp_vertex.normal_index];
           memcpy(gltf_vertex.uv,          bsp_vertex.uv,          sizeof(float)   * 2);
           memcpy(gltf_vertex.colour,      bsp_vertex.colour,      sizeof(uint8_t) * 4);
           memcpy(gltf_vertex.lightmap_uv, bsp_vertex.lightmap.uv, sizeof(float)   * 2);
           vertex_buffer.emplace_back(gltf_vertex);
        }
        for (const auto &bsp_vertex : VERTEX_LIT_BUMP) {
           gltf_vertex.position = VERTICES[bsp_vertex.position_index];
           gltf_vertex.normal   = VERTEX_NORMALS[bsp_vertex.normal_index];
           memcpy(gltf_vertex.uv,          bsp_vertex.uv,          sizeof(float)   * 2);
           memcpy(gltf_vertex.colour,      bsp_vertex.colour,      sizeof(uint8_t) * 4);
           memcpy(gltf_vertex.lightmap_uv, bsp_vertex.lightmap.uv, sizeof(float)   * 2);
           vertex_buffer.emplace_back(gltf_vertex);
        }
        for (const auto &bsp_vertex : VERTEX_UNLIT_TS) {
           gltf_vertex.position = VERTICES[bsp_vertex.position_index];
           gltf_vertex.normal   = VERTEX_NORMALS[bsp_vertex.normal_index];
           memcpy(gltf_vertex.uv,     bsp_vertex.uv,     sizeof(float)   * 2);
           memcpy(gltf_vertex.colour, bsp_vertex.colour, sizeof(uint8_t) * 4);
           memset(gltf_vertex.lightmap_uv, 0, sizeof(float) * 2);
           vertex_buffer.emplace_back(gltf_vertex);
        }
        unsigned int VERTEX_UNLIT_OFFSET    = 0;
        unsigned int VERTEX_LIT_FLAT_OFFSET = VERTEX_UNLIT.size();
        unsigned int VERTEX_LIT_BUMP_OFFSET = VERTEX_LIT_FLAT_OFFSET + VERTEX_LIT_FLAT.size();
        unsigned int VERTEX_UNLIT_TS_OFFSET = VERTEX_LIT_BUMP_OFFSET + VERTEX_LIT_BUMP.size();

        // index buffer
        auto worldspawn = MODELS[0];
        // TODO: metadata
        // -- worldspawn.min & max -> bufferView min & max
        for (int j = 0; j <= static_cast<int>(worldspawn.num_meshes); j++) {
            auto mesh = MESHES[j];
            unsigned int  gltf_offset;
            switch (mesh.flags & 0x600) {
                case MeshFlags::VERTEX_UNLIT:     gltf_offset = VERTEX_UNLIT_OFFSET;     break;
                case MeshFlags::VERTEX_LIT_FLAT:  gltf_offset = VERTEX_LIT_FLAT_OFFSET;  break;
                case MeshFlags::VERTEX_LIT_BUMP:  gltf_offset = VERTEX_LIT_BUMP_OFFSET;  break;
                case MeshFlags::VERTEX_UNLIT_TS:  gltf_offset = VERTEX_UNLIT_TS_OFFSET;  break;
            }
            auto material_sort = MATERIAL_SORTS[mesh.material_sort];
            const int start = static_cast<int>(mesh.first_mesh_index);
            const int end = start + mesh.num_triangles * 3;
            std::vector<int>  indices;
            for (int k = start; k <= end; k++) {
                auto mesh_index = MESH_INDICES[k];
                indices.push_back(material_sort.vertex_offset + mesh_index + gltf_offset);
            }
            // TODO: metadata (bsp Mesh -> gltf mesh primitive
            // -- match span of indices (start, length) to MaterialSort
            // -- material, indices bufferView, bufferView min & max indices
        }

        // write .bin
        char           bin_filename[4096];
        std::ofstream  outfile;
        #define WRITE_BIN(n, v, T) \
            sprintf(bin_filename, "%s.%s.bin", filename, n); \
            outfile.open(bin_filename, std::ios::out | std::ios::binary); \
            outfile.write(reinterpret_cast<char*>(&v[0]), v.size() * sizeof(T)); \
            outfile.close();  outfile.clear()
        WRITE_BIN("index",  index_buffer,  uint32_t);
        WRITE_BIN("vertex", vertex_buffer, VertexGLTF);
        #undef WRITE_BIN

        // write .gltf
        // fopen(...)
        // fprintf(gltf_file, "json template %s %d etc.\n")
        // "uri": "%s.%s.bin", filename, "vertex"
        // "uri": "%s.%s.bin", filename, "index"
        // fclose(...)
    }
    return 0;
}
