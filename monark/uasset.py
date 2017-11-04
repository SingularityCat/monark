"""
ARK uasset compression format:
 - integers are little endian unless specified otherwise

bytes  8: magic and 'format', 2 32-bit integers:
            1: the "unreal signature": 0x9e2a83c1    (c1 83 2a 9e)
            2: unclear, might be compression method? (00 00 00 00)
bytes 24: header, 3 64-bit integers
            1: chunk size
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


class UassetError(Exception):
    """Base class of uasset module exceptions"""


class FormatVersionError(UassetError):
    """Indicates compression file signature problems"""


class InconsistencyError(UassetError):
    """Indicates values don't quite add up"""


class DecompressionError(UassetError):
    """Indicates an error encountered while  decompressing"""


UNREAL_MAGIC = b"\xc1\x83\x2a\x9e"  # 0x9e2a83c1 LE
UASSET_Z_VER = b"\x00\x00\x00\x00"

V00_MAGIC = UNREAL_MAGIC + UASSET_Z_VER

def decompress(source, dest):
    """
    Decompresses a compressed uasset (".uasset.z")

    :param source:  stream to read compressed data from
    :param dest:    stream to write uncompressed data to
    :raises FormatVersionError: raised if the signature/version magic is wrong
    :raises InconsistencyError: raised if header values don't add up
    :raises DecompressionError: rasied if there is any problem decompressing
    """
    magic = source.read(8)
    if magic != V00_MAGIC:
        raise FormatVersionError("unrecognised magic")

    chunk_size, compressed_total, uncompressed_total = \
        struct.unpack("<QQQ", source.read(24))

    chunk_headers = []
    while compressed_total > 0 or uncompressed_total > 0:

        chunk_compressed_size, chunk_uncompressed_size = \
            struct.unpack("<QQ", source.read(16))
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
        if len(chunk) != chunk_compressed_size:
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
