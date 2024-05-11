import struct

from PIL import Image


class LightmapHeader:
    """same struct in all Titanfall Engine Games"""
    flags: int
    width: int
    height: int

    def __init__(self, flags, width, height):
        self.flags, self.width, self.height = flags, width, height

    @classmethod
    def from_bytes(cls, raw: bytes):
        return cls(*struct.unpack("I2H", raw))

    @classmethod
    def from_stream(cls, stream):
        return cls.from_bytes(stream.read(8))


lump = {
    "LIGHTMAP_HEADERS": 0x53,
    "LIGHTMAP_DATA_SKY": 0x62,
    "LIGHTMAP_DATA_REAL_TIME_LIGHTS": 0x69}


def lump_header(bsp_file, lump_name: str) -> (int, int):
    bsp_file.seek(0x10 + (lump[lump_name] * 0x10))
    return struct.unpack("2I", bsp_file.read(8))  # offset, length


bsp_spec = {
    b"rBSP" + version.to_bytes(4, "little"): game
    for version, game in {
        29: "Titanfall",  # and Titanfall: Online
        36: "Titanfall 2 Tech Test",
        37: "Titanfall 2",
        47: "Apex Legends (Season 0-6)",
        48: "Apex Legends (Season 7)",
        49: "Apex Legends (Season 8-9)",
        50: "Apex Legends (Season 10)"}.items()}
bsp_spec.update({
    b"rBSP" + major.to_bytes(2, "little") + minor.to_bytes(2, "little"): game
    for (major, minor), game in {
        (49, 1): "Apex Legends (Season 11)",  # season 10 & 11 depot wierdness
        (50, 1): "Apex Legends (Season 11-12)",
        (51, 1): "Apex Legends (Season 13-20)",
        (52, 1): "Apex Legends (Season 21)"}.items()})


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 4:
        print(f"usage: {sys.argv[0]} OLD_BSP NEW_BSP LIGHTMAPS_FOLDER")
        sys.exit()
    old_bsp_filename, new_bsp_filename, lightmaps_folder = sys.argv[1:]
    # parse bsp
    with open(old_bsp_filename, "rb") as bsp_file:
        # check .bsp is valid
        game = bsp_spec.get(bsp_file.read(8), "Unsupported")
        if game == "Unsupported":
            raise RuntimeError("Unsupported .bsp format!")
        # parse headers
        offset, length = lump_header(bsp_file, "LIGHTMAP_HEADERS")
        bsp_file.seek(offset)
        lightmap_headers = [LightmapHeader.from_stream(bsp_file) for i in range(length // 8)]
        lightmap_data_headers = {L: lump_header(bsp_file, f"LIGHTMAP_DATA_{L}") for L in ("SKY", "REAL_TIME_LIGHTS")}
        lump_order = sorted(lightmap_data_headers, key=lambda k: lightmap_data_headers[k])
        # remove old lightmaps
        raw_bsp = list()  # all bytes except for the lumps we write
        bsp_file.seek(0)
        offset, length = lightmap_data_headers[lump_order[0]]
        raw_bsp.append(bsp_file.read(offset))
        assert bsp_file.tell() == offset
        bsp_file.seek(offset + length)
        offset, length = lightmap_data_headers[lump_order[1]]
        raw_bsp.append(bsp_file.read(bsp_file.tell() - offset))
        assert bsp_file.tell() == offset
        bsp_file.seek(offset + length)
        raw_bsp.append(bsp_file.read())  # until EOF
    # load lightmaps from files
    import os
    lightmap_files = dict(os.path.splitext(fn) for fn in os.listdir(lightmaps_folder))
    # ^ {"SKY.A.0": ".tga"}
    # verify all lightmaps are available
    # NOTE: expects "SKY.A.0.ext", will not find "mp_whatever.SKY.A.0.ext"
    needs = {
        "Titanfall": ("SKY.A", "SKY.B", "RTL"),
        "Titanfall 2": ("SKY.A", "SKY.B", "RTL.A", "RTL.B", "RTL.C")}
    needs["Titanfall 2 Tech Test"] = needs["Titanfall 2"]
    # NOTE: Titanfall 2 .bsp_lump has no RTL.C
    needs.update({
        game: ("SKY.A", "SKY.B", "RTL.A", "RTL.B")
        for game in bsp_spec.values()
        if game.startswith("Apex Legends")})
    # NOTE: there could be some variation between seasons, I haven't checked
    has = {
        f"{lightmap}.{index}": f"{lightmap}.{index}" in lightmap_files
        for index, header in enumerate(lightmap_headers)
        for lightmap in needs[game]}
    if set(has.values()) != {True}:  # don't has what we needs
        missing = sorted([fn for fn in has if has[fn] is False])
        raise FileNotFoundError("Couldn't find files for the following lightmaps:\n" + "\n".join(missing))
    # load lightmap images
    lightmap_images = {
        fn: Image.open(os.path.join(lightmaps_folder, fn + lightmap_files[fn]))
        for fn in has}
    # verify dimensions (all full size EXCEPT r5 RTL.B [half size])
    for i, header in enumerate(lightmap_headers):
        for lightmap in needs[game]:
            width, height = lightmap_images[f"{lightmap}.{i}"].size
            target = f"({header.width}x{header.height})"
            actual = f"({width}x{height})"
            error_msg = f"{lightmap}.{i} {actual} != {target}"
            if (game.startswith("Apex Legends") and lightmap == "RTL.B") or lightmap == "RTL.C":
                target = f"({header.width // 2}x{header.height // 2})"
                error_msg = f"{lightmap}.{i} {actual} != {target}"
                assert width == header.width // 2, error_msg
                assert height == header.height // 2, error_msg
            else:  # most lightmaps
                assert width == header.width, error_msg
                assert height == header.height, error_msg
            print(f"{lightmap}.{i} {actual}")
    # organise & merge lightmap bytes
    sky_bytes, rtl_bytes = list(), list()
    for i, header in enumerate(lightmap_headers):
        # SKY (the same in all games)
        sky_bytes.append(lightmap_images[f"SKY.A.{i}"].tobytes())
        sky_bytes.append(lightmap_images[f"SKY.B.{i}"].tobytes())
        # REAL_TIME_LIGHTS
        if game == "Titanfall":
            rtl_bytes.append(lightmap_images[f"RTL.{i}"].tobytes())
        else:
            rtl_bytes.append(lightmap_images[f"RTL.A.{i}"].tobytes())
            rtl_bytes.append(lightmap_images[f"RTL.B.{i}"].tobytes())
        if "RTL.C" in needs[game]:
            rtl_bytes.append(lightmap_images[f"RTL.C.{i}"].tobytes())
    lightmap_bytes = {
        "SKY": b"".join(sky_bytes),
        "REAL_TIME_LIGHTS": b"".join(rtl_bytes)}
    assert len(lightmap_bytes["SKY"]) == lightmap_data_headers["SKY"][1]
    assert len(lightmap_bytes["REAL_TIME_LIGHTS"]) == lightmap_data_headers["REAL_TIME_LIGHTS"][1]
    # write bsp
    with open(new_bsp_filename, "wb") as bsp_file:
        bsp_file.write(raw_bsp[0])
        bsp_file.write(lightmap_bytes[lump_order[0]])
        bsp_file.write(raw_bsp[1])
        bsp_file.write(lightmap_bytes[lump_order[1]])
        bsp_file.write(raw_bsp[2])
