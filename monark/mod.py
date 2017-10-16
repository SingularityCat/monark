"""
ARK *.info and *.mod formats.
Integers are little endian unless otherwise noted.


string: Simple lenth-prefixed string used in ARK's things.
  bytes        4: 32-bit unsigned integer, representing string length.
  | byte: part of the null terminated string.
  | repeats for the length of the string


ARK mod.info file format:
string: map name
bytes 4: 32-bit integer number of map filenames
| string: map filename
| repeats for the number of maps.
bytes        8: Stuff? Not sure...


ARK modmeta.info format: Seems to be a binary KVP format
bytes 4: 32-bit integer number of KVPs
| string: key
| string: value
| repeats for the number of KVPs.


ARK <modid>.mod file format:
bytes 8: 64-bit integer, mod id
string: mod name
string: mod path
bytes 4: 32-bit unsigned integer, number of maps
| string: map filename
| repeats for the number of maps.
bytes 8: specifically, these ones: 33 FF 22 FF 02 00 00 00 01 (modmeta signature?)
<modmeta.info follows>
"""

import io
import struct
import collections

from typing import Tuple, Union, Sequence, Mapping

# Utility functions:
# ------------------

# integer r/w

def read_u32(source) -> int:
    d, = struct.unpack("<L", source.read(4))
    return d


def read_u64(source) -> int:
    q, = struct.unpack("<Q", source.read(4))
    return q


def write_u32(dest, d: int):
    dest.write(struct.pack("<L", d))


def write_u64(dest, q: int):
    dest.write(struct.pack("<Q", q))


# string r/w

def read_string(source) -> str:
    strlen, = read_u32(source)
    string = source.read(strlen)
    return string[:-1]  # remove null byte


def write_string(dest, string: bytes):
    write_u32(dest, len(string) + 1)
    dest.write(string + b"\x00")


def read_string_array(source) -> Sequence[str]:
    items = []
    n_items = read_u32(source)
    for _ in range(0, n_items):
        items.append(read_string(source))
    return items

def write_string_array(dest, items: Sequence[str]):
    write_u32(len(items))
    for item in items:
        write_string(item)


# kvp r/w

def read_kvps(source) -> Sequence[Tuple[str, str]]:
    """Read """
    kvps = []
    n_kvps = read_u32(source)
    for _ in range(0, n_kvps):
        kvps.append((read_string(source), read_string(source)))
    return kvps

def write_kvps(source, kvps: Sequence[Tuple[str, str]]):
    write_u32(source, len(kvps))
    for k, v in kvps:
        write_string(source, k)
        write_string(source, v)


# specific file parsers
# ---------------------

ARK_MODFILE_MAGIC = b"\x33\xFF\x22\xFF\x02\x00\x00\x00\x01"



ArkModInfo = collections.namedtuple("ArkModInfo", (
    "map_name",         # str
    "map_filenames",    # list of str
    "unknown_data"      # 8 bytes of stuff?
))


def ark_unpack_mod_info(data: bytes) -> ArkModInfo:
    source = io.BytesIO(data)
    return ArkModInfo(
        read_string(source),
        read_string_array(source),
        source.read(8)
    )


def ark_pack_mod_info(struct: ArkModInfo) -> bytes:
    dest = io.BytesIO()
    write_string(struct[0])
    write_string_array(struct[1])
    dest.write(struct[2])
    return dest.getvalue()


ArkModMetaInfo = collections.namedtuple("ArkModMetaInfo", (
    "kvps",             # list of (str, str) tuples
))


def ark_unpack_modmeta_info(data: bytes) -> ArkModMetaInfo:
    source = io.BytesIO(data)
    return ArkModMetaInfo(read_kvps(source))


def ark_pack_modmeta_info(struct: ArkModMetaInfo) -> bytes:
    dest = io.BytesIO()
    write_kvps(dest, struct[0])
    return dest.getvalue()


ArkModfile = collections.namedtuple("ArkModfile", (
    "mod_id",           # int
    "mod_name",         # str
    "mod_path",         # str
    "map_filenames",    # list of str
    "mod_magic",        # 8 bytes of stuff? seems to be the same in every mod file.
    "metadata"          # list of (str, str) tuples
))


def ark_unpack_modfile(data: bytes) -> ArkModfile:
    source = io.BytesIO(data)
    return ArkModfile(
        read_u64(source),
        read_string(source),
        read_string(source),
        read_string_array(source),
        source.read(8),
        read_kvps(source)
    )


def ark_pack_modfile(struct: ArkModfile) -> bytes:
    dest = io.BytesIO()
    write_u64(struct[0])
    write_string(struct[1])
    write_string(struct[2])
    write_string_array(struct[3])
    dest.write(struct[4])
    write_kvps(struct[5])
    return dest.getvalue()


DEFAULT_MOD_PATH_TPL = "../../../ShooterGame/Content/Mods/{modid}"
DEFAULT_MOD_METADATA = [(b"ModType", b"1")]


def ark_gen_modfile(modid: Union[int, str], modinfo: bytes, modmetainfo: bytes=None, mod_path_tpl: str=DEFAULT_MOD_PATH_TPL) -> bytes:

    mi = ark_unpack_mod_info(modinfo)
    if modmetainfo is not None:
        mmi = ark_unpack_modmeta_info(modmetainfo)
        meta_kvps = mmi.kvps
    else:
        meta_kvps = DEFAULT_MOD_METADATA

    amf = ArkModfile(
        int(modid),
        mi.map_name,
        mod_path_tpl.format(modid=modid).encode("utf8"),
        mi.map_filenames,
        ARK_MODFILE_MAGIC,
        meta_kvps
    )

    return ark_pack_modfile(amf)
