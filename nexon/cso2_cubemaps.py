"""extracts VTFEdit friendly cubemaps from CSO2 PAKFILE .vtfs"""
from __future__ import annotations
import lzma
import os
import struct
from typing import Any, List, Tuple, Union


def read_struct(file, format_: str) -> Union[Any, List[Any]]:
    out = struct.unpack(format_, file.read(struct.calcsize(format_)))
    if len(out) == 1:
        out = out[0]
    return out


# taken from bsp_tool/lumps.py
def decompress_valve_LZMA(data: bytes) -> bytes:
    """valve LZMA header adapter"""
    magic, true_size, compressed_size, properties = struct.unpack("4s2I5s", data[:17])
    assert magic == b"LZMA"
    _filter = lzma._decode_filter_properties(lzma.FILTER_LZMA1, properties)
    decompressor = lzma.LZMADecompressor(lzma.FORMAT_RAW, None, [_filter])
    decompressed_data = decompressor.decompress(data[17:17 + compressed_size])
    return decompressed_data[:true_size]  # trim any excess bytes


# def write_struct(file, format_: str, *args):
#     file.write(struct.pack(format_, *args))


class CO2:
    """Counter-Strike: Online 2 compressed .vtf container"""
    filename: str
    header: Tuple[int]  # indices of LZMA blocks?
    vtf_bytes: bytes  # decompressed internal .vtf

    def __repr__(self) -> str:
        return f"<CO2 '{self.filename}' @ 0x{id(self):0X16}>"

    @classmethod
    def from_file(cls, path: str) -> CO2:
        out = cls()
        out.filename = os.path.basename(path)
        with open(path, "rb") as vtf_file:
            magic = vtf_file.read(3)
            assert magic == b"CO2"
            num_blocks = read_struct(vtf_file, "B")
            # 1 + 2x num_blocks uint32_t?
            if num_blocks == 3:
                out.header = read_struct(vtf_file, "7I")
            elif num_blocks == 5:
                out.header = read_struct(vtf_file, "11I")
            else:
                raise NotImplementedError(f"unexpected num_blocks: {num_blocks}")
            data = vtf_file.read()
            blocks = [b"LZMA" + b for b in data.split(b"LZMA")[1:]]
            assert len(blocks) == num_blocks
            out.vtf_bytes = b"".join(map(decompress_valve_LZMA, blocks))
            return out

    # TODO: save_as
