#include <cstdio>
#include <cstring>
#include <vector>

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
    // theory: tangent is .rg values of normal map, sampled at vertex
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
    // TODO: convert position to .gltf coordinate system (Y+ up / rotate -90 X)
    // NOTE: we could do a unique VertexStruct & accessors for each Vertex type
    // -- this would reduce filesize, at the cost of splitting up meshes
    #define COPY_VERTEX_BASE() \
        Vertex  z_up = VERTICES[bsp_vertex.position_index];\
        gltf_vertex.position.x =  z_up.x; \
        gltf_vertex.position.y =  z_up.z; \
        gltf_vertex.position.z = -z_up.y; \
        gltf_vertex.normal   = VERTEX_NORMALS[bsp_vertex.normal_index]; \
        memcpy(gltf_vertex.uv,     bsp_vertex.uv,     sizeof(float)   * 2); \
        memcpy(gltf_vertex.colour, bsp_vertex.colour, sizeof(uint8_t) * 4)
    for (const auto &bsp_vertex : VERTEX_UNLIT) {
        COPY_VERTEX_BASE();
        memset(gltf_vertex.lightmap_uv,   0, sizeof(float) * 2);
        memset(gltf_vertex.lightmap_step, 0, sizeof(float) * 2);
        vertex_buffer.emplace_back(gltf_vertex);
    }
    for (const auto &bsp_vertex : VERTEX_LIT_FLAT) {
        COPY_VERTEX_BASE();
        memcpy(gltf_vertex.lightmap_uv,   bsp_vertex.lightmap.uv,   sizeof(float) * 2);
        memcpy(gltf_vertex.lightmap_step, bsp_vertex.lightmap.step, sizeof(float) * 2);
        vertex_buffer.emplace_back(gltf_vertex);
    }
    for (const auto &bsp_vertex : VERTEX_LIT_BUMP) {
        COPY_VERTEX_BASE();
        memcpy(gltf_vertex.lightmap_uv,   bsp_vertex.lightmap.uv,   sizeof(float) * 2);
        memcpy(gltf_vertex.lightmap_step, bsp_vertex.lightmap.step, sizeof(float) * 2);
        // TODO: tangent
        vertex_buffer.emplace_back(gltf_vertex);
    }
    for (const auto &bsp_vertex : VERTEX_UNLIT_TS) {
        COPY_VERTEX_BASE();
        memset(gltf_vertex.lightmap_uv,   0, sizeof(float) * 2);
        memset(gltf_vertex.lightmap_step, 0, sizeof(float) * 2);
        // TODO: tangent
        vertex_buffer.emplace_back(gltf_vertex);
    }
    unsigned int VERTEX_UNLIT_OFFSET    = 0;
    unsigned int VERTEX_LIT_FLAT_OFFSET = VERTEX_UNLIT.size();
    unsigned int VERTEX_LIT_BUMP_OFFSET = VERTEX_LIT_FLAT_OFFSET + VERTEX_LIT_FLAT.size();
    unsigned int VERTEX_UNLIT_TS_OFFSET = VERTEX_LIT_BUMP_OFFSET + VERTEX_LIT_BUMP.size();

    // index buffer
    std::vector<uint32_t>  index_buffer;
    auto  worldspawn = MODELS[0];
    // TODO: mesh.primitive group tracking
    // -- (material, lightmap_index, first_index, num_indices)
    // splitting worldspawn (opaque, transparent, decals, sky etc.) could be nice
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
            default:  gltf_offset = 0;  // TODO: std::unreachable (C++23)
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
    fprintf(gltf_file, " \"meshes\": [{\"primitives\": [\n");
    fprintf(gltf_file, "{\"attributes\": {\"POSITION\": 0, \"NORMAL\": 1, \"TEXCOORD_0\": 2, " \
                       "\"COLOR_0\": 3, \"TEXCOORD_1\": 4, \"TEXCOORD_2\": 5}, \"indices\": 6}]}],\n");
    // NOTE: gltf.mesh.primitive.attribute & indices index into gltf.accessors
    // TODO: 1 gltf.mesh per bsp.model
    // TODO: translate gltf.mesh to bsp.model origin (requires entity parsing)
    // -- could update the .json w/ bsp_tool
    // TODO: 1 gltf.mesh.primitive per bsp.model.mesh
    // TODO: 1 gltf.material per bsp.material_sort (unique material_name + lightmap_index)
    fprintf(gltf_file, " \"buffers\": [\n");
    fprintf(gltf_file, "  {\"uri\": \"bsp.vertex.bin\", \"byteLength\": %lu},\n", vertex_buffer_length);
    fprintf(gltf_file, "  {\"uri\": \"bsp.index.bin\", \"byteLength\": %lu}],\n", index_buffer_length);
    fprintf(gltf_file, " \"bufferViews\": [\n");
    fprintf(gltf_file, "  {\"buffer\": 0, \"byteLength\": %lu, \"target\": %d, \"byteStride\": %lu},\n",
                       vertex_buffer_length, ARRAY_BUFFER, sizeof(VertexGLTF));
    fprintf(gltf_file, "  {\"buffer\": 1, \"byteLength\": %lu, \"target\": %d}],\n",
                       index_buffer_length, ELEMENT_ARRAY_BUFFER);
    // TODO: accessor mins & maxs
    fprintf(gltf_file, " \"accessors\": [\n");
    #define VERTEX_ATTR(T1, T2, m)  fprintf(gltf_file, \
        "  {\"bufferView\": 0, \"count\": %lu, \"type\": \"%s\", \"componentType\": %d, \"byteOffset\": %lu},\n", \
        vertex_buffer.size(), #T1, T2, offsetof(VertexGLTF, m))
    VERTEX_ATTR(VEC3, FLOAT,         position);
    VERTEX_ATTR(VEC3, FLOAT,         normal);
    VERTEX_ATTR(VEC2, FLOAT,         uv);
    VERTEX_ATTR(VEC4, UNSIGNED_BYTE, colour);
    VERTEX_ATTR(VEC2, FLOAT,         lightmap_uv);
    VERTEX_ATTR(VEC2, FLOAT,         lightmap_step);
    #undef VERTEX_ATTR
    fprintf(gltf_file, "  {\"bufferView\": 1, \"count\": %lu, \"type\": \"SCALAR\", \"componentType\": %d}],\n",
                       index_buffer.size(), UNSIGNED_INT);
    fprintf(gltf_file, " \"asset\": {\"version\": \"2.0\"}}\n");
    fclose(gltf_file);
    return 0;
}
