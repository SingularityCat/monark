#!/usr/bin/python3
import os
import shutil

import io
import struct
import zlib

# ARK asset compression format:
# bytes  8: magic and format version (should be c1 83 2a 9e 00 00 00 00)
# bytes 24: header, 3 64-bit integers
#               1: chunk size
#               2: compressed total
#               3: uncompressed total
# | bytes 16: chunk headers, 2 64-bit integers
# |             1: compressed size
# |             2: uncomessed size
# | repeats until sum(compressed size) == compressed total


# TODO: add proper exceptions
def ark_asset_decompress(source, dest):
    magic = source.read(8)
    if magic != b"\xc1\x83\x2a\x9e\x00\x00\x00\x00":
        raise Exception("crap")

    chunk_size, compressed_total, uncompressed_total = \
        struct.unpack("<QQQ", source.read(24))

    chunk_headers = []
    while compressed_total > 0:

        chunk_compressed_size, chunk_uncompressed_size = \
            struct.unpack("<QQ", source.read(16))
        chunk_headers.append((chunk_compressed_size, chunk_uncompressed_size))
        compressed_total -= chunk_compressed_size

    for chunk_compressed_size, chunk_uncompressed_size in chunk_headers:
        chunk = zlib.decompress(source.read(chunk_compressed_size))
        if len(chunk) != chunk_uncompressed_size:
            raise Exception("crap")
        dest.write(chunk)
        uncompressed_total -= chunk_uncompressed_size

    if uncompressed_total != 0:
        raise Exception("crap")


# string: Simple lenth-prefixed string used in ARK's things.
#   bytes        4: 32-bit unsigned integer, representing string length.
#   | byte: part of the null terminated string.
#   | repeats for the length of the string

# ARK mod.info file format:
# string: map name
# bytes 4: 32-bit integer number of map filenames
# | string: map filename
# | repeats for the number of maps.
# bytes        8: Stuff? Not sure...

# ARK modmeta.info format: Seems to be a binary KVP format
# bytes 4: 32-bit integer number of KVPs
# | string: key
# | string: value
# | repeats for the number of KVPs.

# ARK <modid>.mod file format:
# bytes 8: 64-bit integer, mod id
# string: mod name
# string: mod path
# bytes 4: 32-bit integer, number of maps
# | string: map filename
# | repeats for the number of maps.
# bytes 8: specifically, these ones: 33 FF 22 FF 02 00 00 00 01 (modmeta signature?)
# <modmeta.info follows>
#
# Default "modmeta.info" is this:
#    ModType=1
#  or: "\x01\x00\x00\x00\x08\x00\x00\x00ModType\x00\x02\x00\x00\x001\x00"


def ark_read_string(source):
    strlen, = struct.unpack("<L", source.read(4))
    string = source.read(strlen)
    return string[:-1]  # remove null byte


def ark_write_string(dest, string: bytes):
    dest.write(struct.pack("<L", len(string) + 1) + string + b"\x00")


def ark_modfile_create(modid, modinfo: bytes, modmetainfo: bytes=None):
    source = io.BytesIO(modinfo)
    output = io.BytesIO()

    map_name = ark_read_string(source)
    n_maps, = struct.unpack("<L", source.read(4))

    output.write(struct.pack("<Q", int(modid)))
    ark_write_string(output, map_name)
    ark_write_string(output, "../../../ShooterGame/Content/Mods/{0}".format(modid).encode())
    output.write(struct.pack("<L", n_maps))

    for i in range(0, n_maps):
        map_filename = ark_read_string(source)
        ark_write_string(output, map_filename)

    output.write(b"\x33\xFF\x22\xFF\x02\x00\x00\x00\x01")

    if modmetainfo is not None:
        output.write(modmetainfo)
    else:
        output.write(b"\x01\x00\x00\x00\x08\x00\x00\x00ModType\x00\x02\x00\x00\x001\x00")

    return output.getvalue()


mod_dir = "../steamapps/workshop/content/346110"
mod_dst = "../ShooterGame/Content/Mods"
sub_dir = "WindowsNoEditor"
#sub_dir = "LinuxNoEditor"

root_dirfd = os.open(".", os.O_RDONLY)

for modid in os.listdir(mod_dir):
    os.mkdir(os.path.join(mod_dst, modid))
    src_dirfd = os.open(os.path.join(mod_dir, modid, sub_dir), os.O_RDONLY)
    dst_dirfd = os.open(os.path.join(mod_dst, modid), os.O_RDONLY)

    os.chdir(src_dirfd)

    # Copy/decompress files from src_dirfd to dest_dirfd
    for dirpath, dirnames, filenames in os.walk("."):
        for dirname in dirnames:
            os.mkdir(os.path.join(dirpath, dirname), dir_fd=dst_dirfd)
        for filename in filenames:
            if filename.endswith(".z.uncompressed_size"):
                # who cares?
                continue

            srcname = dstname = os.path.join(dirpath, filename)
            if filename.endswith(".z"):
                dstname = os.path.join(dirpath, filename[:-2])

            srcfd = os.open(srcname, os.O_RDONLY, dir_fd=src_dirfd)
            dstfd = os.open(dstname, os.O_WRONLY | os.O_CREAT, dir_fd=dst_dirfd)
            with os.fdopen(srcfd, "rb") as src, os.fdopen(dstfd, "wb") as dst:
                if filename.endswith(".z"):
                    ark_asset_decompress(src, dst)
                else:
                    dst.write(src.read())

    with open("mod.info", "rb") as mif:
        mod_info = mif.read()

    if os.path.exists("modmeta.info"):
        with open("modmeta.info", "rb") as mmif:
            modmeta_info = mmif.read()
    else:
        modmeta_info = None

    os.chdir(root_dirfd)

    modmod = ark_modfile_create(modid, mod_info, modmeta_info)
    with open(os.path.join(mod_dst, modid + ".mod"), "wb") as mf:
        mf.write(modmod)

    os.close(src_dirfd)
    os.close(dst_dirfd)

os.close(root_dirfd)
