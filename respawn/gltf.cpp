#include <cstdio>
#include <cstring>

#include "gltf.hpp"


typedef struct {
    Vertex   position;          // float          VEC3  POSITION
    Vertex   normal;            // float          VEC3  NORMAL
    float    uv[2];             // float          VEC2  TEXCOORD_0
    uint8_t  colour[4];         // unsigned byte  VEC4  COLOR_0
    float    lightmap_uv[2];    // float          VEC2  TEXCOORD_1
    float    lightmap_step[2];  // float          VEC2  TEXCOORD_2
    // theory: lightmap_step is added to lightmap uv (increments w/ style)
    // TODO: int32_t  tangent[2];  => float  tangent[4]  (float VEC4 TANGENT)
} VertexGLTF;


// .gltf constants
// accessor.componentType
// const int BYTE = 5120;
const int UNSIGNED_BYTE = 5121;
// const int SHORT = 5122;
// const int UNSIGNED_SHORT = 5123;
const int UNSIGNED_INT = 5125;
const int FLOAT = 5126;
// bufferView.target
const int ARRAY_BUFFER         = 34962;
const int ELEMENT_ARRAY_BUFFER = 34963;


// TODO: need some struct / class to carry json metadata per mesh
// span { start, length } -> { bufferOffset, byteLength }
// MaterialSort.{lightmap,cubemap}_index

// TODO: lightmaps -> .png
// NOTE: format is different between r1 & r2
// SKY_A_0, ..._B_0, ..._1, etc.
// RTL_A_0, ..._B_0, ..._1, etc.


int main(int argc, char* argv[]) {
    // TODO: generate .glb (need to know filesizes for .bin & .gltf)
    // TODO: .glb -> stdout
    // NOTE: all in one file means embedding lightmaps as base-64 URI
    if (argc != 2) {
        printf("Usage: %s FILENAME\n", argv[0]);
        return 0;
    }
    char* filename = argv[1];

    // load bsp data
    RespawnBsp  bsp(filename);
    if (!bsp.is_valid()) {
        fprintf(stderr, "%s is not a Titanfall / Titanfall 2 .bsp!\n", filename);
        return 0;
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
    // vertex buffer
    std::vector<VertexGLTF>  vertex_buffer;
    VertexGLTF  gltf_vertex;
    // TODO: VEC4 tangent & maybe lightmap step
    for (const auto &bsp_vertex : VERTEX_UNLIT) {
       gltf_vertex.position = VERTICES[bsp_vertex.position_index];
       gltf_vertex.normal   = VERTEX_NORMALS[bsp_vertex.normal_index];
       memcpy(gltf_vertex.uv,     bsp_vertex.uv,     sizeof(float)   * 2);
       memcpy(gltf_vertex.colour, bsp_vertex.colour, sizeof(uint8_t) * 4);
       memset(gltf_vertex.lightmap_uv,   0, sizeof(float) * 2);
       memset(gltf_vertex.lightmap_step, 0, sizeof(float) * 2);
       vertex_buffer.emplace_back(gltf_vertex);
    }
    for (const auto &bsp_vertex : VERTEX_LIT_FLAT) {
       gltf_vertex.position = VERTICES[bsp_vertex.position_index];
       gltf_vertex.normal   = VERTEX_NORMALS[bsp_vertex.normal_index];
       memcpy(gltf_vertex.uv,            bsp_vertex.uv,            sizeof(float)   * 2);
       memcpy(gltf_vertex.colour,        bsp_vertex.colour,        sizeof(uint8_t) * 4);
       memcpy(gltf_vertex.lightmap_uv,   bsp_vertex.lightmap.uv,   sizeof(float)   * 2);
       memcpy(gltf_vertex.lightmap_step, bsp_vertex.lightmap.step, sizeof(float)   * 2);
       vertex_buffer.emplace_back(gltf_vertex);
    }
    for (const auto &bsp_vertex : VERTEX_LIT_BUMP) {
       gltf_vertex.position = VERTICES[bsp_vertex.position_index];
       gltf_vertex.normal   = VERTEX_NORMALS[bsp_vertex.normal_index];
       memcpy(gltf_vertex.uv,            bsp_vertex.uv,            sizeof(float)   * 2);
       memcpy(gltf_vertex.colour,        bsp_vertex.colour,        sizeof(uint8_t) * 4);
       memcpy(gltf_vertex.lightmap_uv,   bsp_vertex.lightmap.uv,   sizeof(float)   * 2);
       memcpy(gltf_vertex.lightmap_step, bsp_vertex.lightmap.step, sizeof(float)   * 2);
       // TODO: convert tangent to VEC4
       vertex_buffer.emplace_back(gltf_vertex);
    }
    for (const auto &bsp_vertex : VERTEX_UNLIT_TS) {
       gltf_vertex.position = VERTICES[bsp_vertex.position_index];
       gltf_vertex.normal   = VERTEX_NORMALS[bsp_vertex.normal_index];
       memcpy(gltf_vertex.uv,     bsp_vertex.uv,     sizeof(float)   * 2);
       memcpy(gltf_vertex.colour, bsp_vertex.colour, sizeof(uint8_t) * 4);
       memset(gltf_vertex.lightmap_uv,   0, sizeof(float) * 2);
       memset(gltf_vertex.lightmap_step, 0, sizeof(float) * 2);
       // TODO: convert tangent to VEC4
       vertex_buffer.emplace_back(gltf_vertex);
    }
    unsigned int VERTEX_UNLIT_OFFSET    = 0;
    unsigned int VERTEX_LIT_FLAT_OFFSET = VERTEX_UNLIT.size();
    unsigned int VERTEX_LIT_BUMP_OFFSET = VERTEX_LIT_FLAT_OFFSET + VERTEX_LIT_FLAT.size();
    unsigned int VERTEX_UNLIT_TS_OFFSET = VERTEX_LIT_BUMP_OFFSET + VERTEX_LIT_BUMP.size();

    // index buffer
    std::vector<uint32_t>  index_buffer;
    auto  worldspawn = MODELS[0];
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
        for (int k = start; k < end; k++) {
            auto mesh_index = MESH_INDICES[k];
            index_buffer.push_back(material_sort.vertex_offset + mesh_index + gltf_offset);
        }
        // TODO: metadata (.bsp Mesh -> .gltf mesh primitive
        // -- match span of indices (start, length) to MaterialSort
        // -- material, indices bufferView, bufferView min & max indices
    }

    // write .bin
    char           bin_filename[256];
    std::ofstream  outfile;
    #define WRITE_BIN(n, T) \
        sprintf(bin_filename, "bsp.%s.bin", #n); \
        outfile.open(bin_filename, std::ios::out | std::ios::binary); \
        unsigned long int  n##_buffer_length = n##_buffer.size() * sizeof(T); \
        outfile.write(reinterpret_cast<char*>(&n##_buffer[0]), n##_buffer_length); \
        outfile.close();  outfile.clear()
    WRITE_BIN(index,  uint32_t);
    WRITE_BIN(vertex, VertexGLTF);
    #undef WRITE_BIN

    // write .gltf
    FILE* gltf_file = fopen("bsp.gltf", "w");
    fprintf(gltf_file, "{\"scene\": 0, \"scenes\": [{\"nodes\": [0]}], \"nodes\": [{\"mesh\": 0}],\n");
    fprintf(gltf_file, " \"meshes\": [{\"primitives\": [{\"attributes\": {\n");
    fprintf(gltf_file, "    \"POSITION\": 1,\n");  // accessor indices
    fprintf(gltf_file, "    \"NORMAL\": 2,\n");
    fprintf(gltf_file, "    \"TEXCOORD_0\": 3,\n");
    fprintf(gltf_file, "    \"COLOR_0\": 4,\n");
    fprintf(gltf_file, "    \"TEXCOORD_1\": 5,\n");
    fprintf(gltf_file, "    \"TEXCOORD_2\": 6\n");
    fprintf(gltf_file, "  }, \"indices\": 0}]}],\n");
    fprintf(gltf_file, " \"buffers\": [\n");
    fprintf(gltf_file, "  {\"uri\": \"bsp.index.bin\", \"byteLength\": %lu},\n", index_buffer_length);
    fprintf(gltf_file, "  {\"uri\": \"bsp.vertex.bin\", \"byteLength\": %lu}],\n", vertex_buffer_length);
    fprintf(gltf_file, " \"bufferViews\": [\n");
    fprintf(gltf_file, "  {\"buffer\": 0, \"byteLength\": %lu, \"target\": %d},\n",
                       index_buffer_length, ELEMENT_ARRAY_BUFFER);
    fprintf(gltf_file, "  {\"buffer\": 1, \"byteLength\": %lu, \"target\": %d, \"byteStride\": %lu}],\n",
                       vertex_buffer_length, ARRAY_BUFFER, sizeof(VertexGLTF));
    // TODO: accessor mins & maxs
    fprintf(gltf_file, " \"accessors\": [\n");
    fprintf(gltf_file, "  {\"bufferView\": 0, \"count\": %lu, \"type\": \"SCALAR\", \"componentType\": %d},\n",
                       index_buffer.size(), UNSIGNED_INT);
    #define VERTEX_ATTR(T1, T2, m, e)  fprintf(gltf_file, \
        "  {\"bufferView\": 1, \"count\": %lu, \"type\": \"%s\", \"componentType\": %d, \"byteOffset\": %lu%s\n", \
        vertex_buffer.size(), #T1, T2, offsetof(VertexGLTF, m), e)
    VERTEX_ATTR(VEC3, FLOAT,         position,      "}," );
    VERTEX_ATTR(VEC3, FLOAT,         normal,        "}," );
    VERTEX_ATTR(VEC2, FLOAT,         uv,            "}," );
    VERTEX_ATTR(VEC4, UNSIGNED_BYTE, colour,        "}," );
    VERTEX_ATTR(VEC2, FLOAT,         lightmap_uv,   "}," );
    VERTEX_ATTR(VEC2, FLOAT,         lightmap_step, "}],");
    #undef VERTEX_ATTR
    fprintf(gltf_file, " \"asset\": {\"version\": \"2.0\"}}\n");
    fclose(gltf_file);
    return 0;
}
