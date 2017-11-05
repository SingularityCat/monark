"""
ARK uasset compression format:
 - integers are little endian unless specified otherwise

bytes  8: magic and 'format', 2 32-bit integers:
            1: the "unreal signature": 0x9e2a83c1    (c1 83 2a 9e)
            2: unclear, might be compression method? (00 00 00 00)
bytes 24: header, 3 64-bit integers
            1: chunk size (usually 0x20000)
            2: compressed total
            3: uncompressed total
| bytes 16: chunk headers, 2 64-bit integers
|             1: compressed size
|             2: uncomessed size
| repeats until sum(compressed size) == compressed total

The rest of the file contains the "chunks".
The chunks are just runs of zlib compressed data, each run having a length
corresponding to the "compressed size" field in the chunk headers.
"""

import struct
import zlib
import collections
import io



class UassetZError(Exception):
    """Base class of uasset module exceptions"""


class FormatVersionError(UassetZError):
    """Indicates compression file signature problems"""


class InconsistencyError(UassetZError):
    """Indicates values don't quite add up"""


class DecompressionError(UassetZError):
    """Indicates an error encountered while decompressing"""


UNREAL_MAGIC = b"\xc1\x83\x2a\x9e"  # 0x9e2a83c1 LE
DEFAULT_CHUNK_SIZE = 0x20000        # All ARK mods seem to use this value.


# Utility functions #########################################################

UassetZMainHeader = collections.namedtuple("UassetZMainHeader", (
    "magic",                # integer (presented as string)
    "version",              # 32-bit integer
    "chunk_size",           # integer
    "compressed_total",     # integer
    "uncompressed_total"    # integer
))


def read_main_header(source) -> UassetZMainHeader:
    header = struct.unpack("<4sLQQQ", source.read(32))
    return UassetZMainHeader(*header)


def write_main_header(dest, header: UassetZMainHeader):
    dest.write(struct.pack("<4sLQQQ", *header))


UassetZChunkHeader = collections.namedtuple("UassetZChunkHeader", (
    "chunk_compressed_size",
    "chunk_uncompressed_size"
))


def read_chunk_header(source) -> UassetZChunkHeader:
    header = struct.unpack("<QQ", source.read(16))
    return UassetZChunkHeader(*header)


def write_chunk_header(dest, header: UassetZChunkHeader):
    dest.write(struct.pack("<QQ", *header))


# main functions ############################################################

def decompress(source, dest):
    """
    Decompresses a compressed uasset (".uasset.z")

    :param source:  stream to read compressed data from
    :param dest:    stream to write uncompressed data to
    :raises FormatVersionError: raised if the signature/version magic is wrong
    :raises InconsistencyError: raised if header values don't add up
    :raises DecompressionError: rasied if there is any problem decompressing
    """

    magic, ver, chunk_size, compressed_total, uncompressed_total = \
        read_main_header(source)

    if magic != UNREAL_MAGIC:
        raise FormatVersionError("unrecognised magic")
    if ver != 0:
        raise FormatVersionError("unknown version")

    chunk_headers = []
    while compressed_total > 0 or uncompressed_total > 0:

        chunk_compressed_size, chunk_uncompressed_size = \
            read_chunk_header(source)
        chunk_headers.append((chunk_compressed_size, chunk_uncompressed_size))

        compressed_total -= chunk_compressed_size
        uncompressed_total -= chunk_uncompressed_size

    # sanity checks:
    if uncompressed_total != 0:
        raise InconsistencyError("uncompressed data unaccounted for?")

    if compressed_total != 0:
        raise InconsistencyError("excess compressed data?")

    for chunk_compressed_size, chunk_uncompressed_size in chunk_headers:
        compressed_chunk = source.read(chunk_compressed_size)
        if len(compressed_chunk) != chunk_compressed_size:
            raise DecompressionError(
                "truncated chunk"
            )
        try:
            chunk = zlib.decompress(compressed_chunk)
        except zlib.error as exc:
            raise DecompressionError("zlib chunk decompression error") from exc
        if len(chunk) != chunk_uncompressed_size:
            raise DecompressionError(
                "uncompressed size of chunk does not match chunk header"
            )
        dest.write(chunk)


def compress(source, dest, chunk_size=DEFAULT_CHUNK_SIZE):
    """
    Compresses some data using "uasset.z" compression.

    :param source:      stream to read uncompressed data from
    :param dest:        stream to write compressed data to
    :param chunk_size:  chunk size to use
    """

    compressed_total = 0
    uncompressed_total = 0

    chunk_headers = []
    chunks = []
    while True:
        chunk = source.read(chunk_size)
        if len(chunk) == 0:
            break

        compressed_chunk = zlib.compress(chunk)

        compressed_total += len(compressed_chunk)
        uncompressed_total += len(chunk)

        chunk_headers.append(UassetZChunkHeader(len(compressed_chunk), len(chunk)))
        chunks.append(compressed_chunk)

        if len(chunk) < chunk_size:
            break

    mh = UassetZMainHeader(
        UNREAL_MAGIC, 0,
        chunk_size, compressed_total, uncompressed_total
    )

    write_main_header(dest, mh)
    for ch in chunk_headers:
        write_chunk_header(dest, ch)

    for chunk in chunks:
        dest.write(chunk)
