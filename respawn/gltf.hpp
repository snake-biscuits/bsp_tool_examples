#include <cstdint>
#include <fstream>
#include <vector>


#define INTO(x)  reinterpret_cast<char*>(&x)

typedef struct { uint32_t offset, length, version, fourCC; } LumpHeader;
typedef struct { uint32_t magic, version, revision, _127; LumpHeader lumps[128]; } BspHeader;


class RespawnBsp { public:
    BspHeader      header;
    std::ifstream  file;

    // TODO: verify 'rBSP' magic & 29/37 version

    RespawnBsp(const char* filename) {
        this->file = std::ifstream(filename, std::ios::in | std::ios::binary);
        this->file.read(INTO(this->header), sizeof(BspHeader));
    }

    ~RespawnBsp() {}

    template <typename T>
    void load_lump(const int lump_index, std::vector<T> &lump_vector) {
        auto header = this->header.lumps[lump_index];
        lump_vector.clear();  lump_vector.resize(header.length / sizeof(T));
        this->file.seekg(header.offset);
        this->file.read(INTO(lump_vector[0]), header.length);
    }
};


typedef struct {  // lump 0x52 (82)
    int16_t  texture_data, lightmap_header, cubemap, last_vertex;
    int32_t  vertex_offset;
} MaterialSort;


typedef struct {  // lump 0x50 (80)
    uint32_t  first_mesh_index;
    uint16_t  num_triangles;
    uint16_t  first_vertex, num_vertices;
    uint16_t  vertex_type;
    int8_t    styles[4];
    int16_t   luxel_origin[2];
    uint8_t   luxel_offset_max[2];
    uint16_t  material_sort;
    uint32_t  flags;
} Mesh;


namespace MeshFlags {
    const int  VERTEX_LIT_FLAT = 0x000;
    const int  VERTEX_LIT_BUMP = 0x200;
    const int  VERTEX_UNLIT    = 0x400;
    const int  VERTEX_UNLIT_TS = 0x600;
};


typedef struct {  // lump 0x0E (14)
    float     mins[3], maxs[3];
    uint32_t  first_mesh, num_meshes;
} Model;


typedef struct {  // lump 0x48 (72)
    uint32_t  position_index, normal_index;
    float     uv[2];
    uint8_t   colour[4];
    struct { float uv[2], step[2]; }  lightmap;
} VertexLitFlat;


typedef struct {  // lump 0x03 (3)
    float x, y, z;
} Vertex;


typedef struct {  // lump 0x49 (73)
    uint32_t  position_index, normal_index;
    float     uv[2];
    uint8_t   colour[4];
    struct { float uv[2], step[2]; }  lightmap;
    int32_t   tangent[2];
} VertexLitBump;


typedef struct {  // lump 0x47 (71)
    uint32_t  position_index, normal_index;
    float     uv[2];
    uint8_t   colour[4];
} VertexUnlit;


typedef struct {  // lump 0x4A (74)
    uint32_t  position_index, normal_index;
    float     uv[2];
    uint8_t   colour[4];
    int32_t   tangent[2];
} VertexUnlitTS;
