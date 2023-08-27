#include <cstdio>

#include "gltf.hpp"


int main(int argc, char* argv[]) {
    if (argc == 1) { printf("Usage: %s [FILENAME] ...\n", argv[0]); }
    for (int i = 1; i < argc; i++) {
        char*  filename = argv[i];
        printf("converting %s ...\n", filename);

        // load bsp data
        RespawnBsp  bsp(filename);
        #define LUMP(T, n, i)  std::vector<T>  n;  bsp.load_lump<T>(i, n)
        // LUMP(Vertex,         vertices,           0x03);
        LUMP(Model,          models,             0x0E);
        LUMP(uint16_t,       mesh_indices,       0x4F);
        LUMP(Mesh,           meshes,             0x50);
        LUMP(MaterialSort,   material_sorts,     0x52);
        LUMP(VertexUnlit,    unlit_vertices,     0x47);
        LUMP(VertexLitFlat,  lit_flat_vertices,  0x48);
        LUMP(VertexLitBump,  lit_bump_vertices,  0x49);
        LUMP(VertexUnlitTS,  unlit_ts_vertices,  0x4A);
        #undef LUMP
        bsp.file.close();

        // generate .bin buffer(s)
        std::vector<uint32_t>  buffer;
        auto worldspawn = models[0];
        for (int j = 0; j <= static_cast<int>(worldspawn.num_meshes); j++) {
            auto mesh = meshes[j];
            auto material_sort = material_sorts[mesh.material_sort];
            const int start = static_cast<int>(mesh.first_mesh_index);
            const int end = start + mesh.num_triangles * 3;
            std::vector<int>  indices;
            for (int k = start; k <= end; k++) {
                auto mesh_index = mesh_indices[k];
                indices.push_back(material_sort.vertex_offset + mesh_index);
            }
            auto vertex_lump = mesh.flags & 0x600;
            #define GET_POSITIONS(a)  for (const auto& v : a) { buffer.push_back(v.position_index); }  break
            switch (vertex_lump) {
                case MeshFlags::VERTEX_LIT_FLAT:  GET_POSITIONS(lit_flat_vertices);
                case MeshFlags::VERTEX_LIT_BUMP:  GET_POSITIONS(lit_bump_vertices);
                case MeshFlags::VERTEX_UNLIT:     GET_POSITIONS(unlit_vertices);
                case MeshFlags::VERTEX_UNLIT_TS:  GET_POSITIONS(unlit_ts_vertices);
            }
            #undef GET_POSITIONS
        }

        // write .bin
        char  bin_filename[4096];
        sprintf(bin_filename, "%s.bin", filename);
        std::ofstream  outfile(bin_filename, std::ios::out | std::ios::binary);
        outfile.write(reinterpret_cast<char*>(&buffer[0]), buffer.size() * sizeof(uint32_t));
        outfile.close();

        // write .gltf
        // fopen(...)
        // fprintf(gltf_file, "json template %s %d etc.\n")
        // "uri": "%s.0003.bsp_lump", filename
        // fclose(...)
    }
    return 0;
}
