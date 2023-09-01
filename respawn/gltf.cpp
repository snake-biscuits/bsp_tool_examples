#include <cstdio>
#include <cstdlib>
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


typedef struct {
    uint32_t     first_byte;
    uint32_t     num_vertices;
    uint32_t     lightmap_index;
    std::string  material_name;
} MetaGLTF;  // gltf.mesh.primitive material, lightmap & vertex range


std::string sanitise(std::string s) {
    // TODO: lowercase
    size_t index = 0;
    while ((index = s.find("\\", 0)) != std::string::npos) {
        s.replace(index, 1, "/");
        index += 1;
    }
    return s;
}


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
    GET_LUMP(TextureData,    TEXTURE_DATA,     0x02);
    GET_LUMP(Vertex,         VERTICES,         0x03);
    GET_LUMP(Model,          MODELS,           0x0E);
    GET_LUMP(Vertex,         VERTEX_NORMALS,   0x1E);
    GET_LUMP(uint32_t,       STRING_TABLE,     0x2C);
    GET_LUMP(uint16_t,       MESH_INDICES,     0x4F);
    GET_LUMP(Mesh,           MESHES,           0x50);
    GET_LUMP(MaterialSort,   MATERIAL_SORTS,   0x52);
    GET_LUMP(VertexUnlit,    VERTEX_UNLIT,     0x47);
    GET_LUMP(VertexLitFlat,  VERTEX_LIT_FLAT,  0x48);
    GET_LUMP(VertexLitBump,  VERTEX_LIT_BUMP,  0x49);
    GET_LUMP(VertexUnlitTS,  VERTEX_UNLIT_TS,  0x4A);
    #undef GET_LUMP
    char* STRING_DATA;
    STRING_DATA = static_cast<char*>(malloc(bsp.header.lumps[0x2B].length));
    bsp.load_lump_raw(0x2B, STRING_DATA);
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
    uint32_t VERTEX_UNLIT_OFFSET    = 0;
    uint32_t VERTEX_LIT_FLAT_OFFSET = VERTEX_UNLIT.size();
    uint32_t VERTEX_LIT_BUMP_OFFSET = VERTEX_LIT_FLAT_OFFSET + VERTEX_LIT_FLAT.size();
    uint32_t VERTEX_UNLIT_TS_OFFSET = VERTEX_LIT_BUMP_OFFSET + VERTEX_LIT_BUMP.size();

    // index buffer metadata
    std::vector<MetaGLTF>  index_meta;
    MetaGLTF  meta;
    uint16_t  previous_material_sort = -1;
    // index buffer
    std::vector<uint32_t>  index_buffer;
    auto  worldspawn = MODELS[0];
    for (int i = 0; i <= static_cast<int>(worldspawn.num_meshes); i++) {
        auto      mesh = MESHES[i];
        uint32_t  gltf_offset;
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
        for (int j = start; j < end; j++) {
            auto mesh_index = MESH_INDICES[j];
            index_buffer.push_back(material_sort.vertex_offset + mesh_index + gltf_offset);
        }
        // metadata
        if (previous_material_sort == (uint16_t) -1) {
            previous_material_sort = mesh.material_sort;
            meta.first_byte     = 0;
            meta.num_vertices   = 0;
            meta.lightmap_index = material_sort.lightmap_header;
            auto  texture_data = TEXTURE_DATA[material_sort.texture_data];
            meta.material_name = sanitise(&STRING_DATA[STRING_TABLE[texture_data.name_index]]);
        }
        if (mesh.material_sort == previous_material_sort) {
            meta.num_vertices += mesh.num_triangles * 3;
        } else {  // changeover
            index_meta.push_back(meta);
            previous_material_sort = mesh.material_sort;
            meta.num_vertices = mesh.num_triangles * 3;
            meta.first_byte = (index_buffer.size() - meta.num_vertices) * sizeof(uint32_t);
            meta.lightmap_index = material_sort.lightmap_header;
            auto  texture_data = TEXTURE_DATA[material_sort.texture_data];
            meta.material_name = sanitise(&STRING_DATA[STRING_TABLE[texture_data.name_index]]);
        }
    }
    index_meta.push_back(meta);

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
    #define WRITE_GLTF(...)  fprintf(gltf_file, __VA_ARGS__)
    WRITE_GLTF("{\"scene\": 0, \"scenes\": [{\"nodes\": [0]}], \"nodes\": [{\"mesh\": 0}],\n");
    // TODO: 1 gltf.mesh per bsp.model
    // TODO: translate gltf.mesh to bsp.model origin (requires entity parsing)
    // -- could update the .json w/ bsp_tool
    WRITE_GLTF(" \"meshes\": [{\"primitives\": [\n");
    #define FOREACH_META  for (unsigned long int i = 0; i < index_meta.size(); i++)
    FOREACH_META {
        WRITE_GLTF("  {\"attributes\": {\"POSITION\": 0, \"NORMAL\": 1, \"TEXCOORD_0\": 2, ");
        WRITE_GLTF("\"COLOR_0\": 3, \"TEXCOORD_1\": 4, \"TEXCOORD_2\": 5}, ");
        WRITE_GLTF("\"indices\": %lu, \"material\": %lu}", 6 + i, i);
        if (i < index_meta.size() - 1) { WRITE_GLTF(",\n");    }
        else                           { WRITE_GLTF("]}],\n"); }
    }
    WRITE_GLTF( "\"materials\": [\n");
    FOREACH_META {
        auto  meta = index_meta[i];
        if (meta.lightmap_index != static_cast<uint32_t>(-1)) {
            WRITE_GLTF("  {\"name\": \"%s.%d\"}", meta.material_name.c_str(), meta.lightmap_index);
        } else {
            WRITE_GLTF("  {\"name\": \"%s\"}", meta.material_name.c_str());  // unlit
        }
        if (i < index_meta.size() - 1) { WRITE_GLTF(",\n");  }
        else                           { WRITE_GLTF("],\n"); }
    }
    WRITE_GLTF(" \"buffers\": [\n");
    WRITE_GLTF("  {\"uri\": \"bsp.vertex.bin\", \"byteLength\": %lu},\n", vertex_buffer_length);
    WRITE_GLTF("  {\"uri\": \"bsp.index.bin\", \"byteLength\": %lu}],\n", index_buffer_length);
    WRITE_GLTF(" \"bufferViews\": [\n");
    WRITE_GLTF("  {\"buffer\": 0, \"byteLength\": %lu, \"target\": %d, \"byteStride\": %lu},\n",
               vertex_buffer_length, ARRAY_BUFFER, sizeof(VertexGLTF));
    WRITE_GLTF("  {\"buffer\": 1, \"byteLength\": %lu, \"target\": %d}],\n",
               index_buffer_length, ELEMENT_ARRAY_BUFFER);
    // TODO: accessor mins & maxs
    WRITE_GLTF(" \"accessors\": [\n");
    #define VERTEX_ATTR(T1, T2, m)  WRITE_GLTF( \
        "  {\"bufferView\": 0, \"count\": %lu, \"type\": \"%s\", \"componentType\": %d, \"byteOffset\": %lu},\n", \
        vertex_buffer.size(), #T1, T2, offsetof(VertexGLTF, m))
    VERTEX_ATTR(VEC3, FLOAT,         position);
    VERTEX_ATTR(VEC3, FLOAT,         normal);
    VERTEX_ATTR(VEC2, FLOAT,         uv);
    VERTEX_ATTR(VEC4, UNSIGNED_BYTE, colour);
    VERTEX_ATTR(VEC2, FLOAT,         lightmap_uv);
    VERTEX_ATTR(VEC2, FLOAT,         lightmap_step);
    #undef VERTEX_ATTR
    // TODO: 1 gltf.accessor (indices) for each MeshMeta
    FOREACH_META {
        auto  meta = index_meta[i];
        WRITE_GLTF("  {\"bufferView\": 1, \"count\": %d, \"byteOffset\": %d, \"type\": \"SCALAR\", \"componentType\": %d}",
                   meta.num_vertices, meta.first_byte, UNSIGNED_INT);
        if (i < index_meta.size() - 1) { WRITE_GLTF(",\n");  }
        else                           { WRITE_GLTF("],\n"); }
    }
    free(STRING_DATA);
    WRITE_GLTF(" \"asset\": {\"version\": \"2.0\"}}\n");
    fclose(gltf_file);
    return 0;
}
