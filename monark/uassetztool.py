import sys

import argparse

from . import uassetz

COMPRESS_ALIASES = {"compress", "c"}
DECOMPRESS_ALIASES = {"decompress", "x"}
INFORMATION_ALIASES = {"information", "t", "?"}

MODE_CHOICES = COMPRESS_ALIASES | DECOMPRESS_ALIASES | INFORMATION_ALIASES


def uassetztool(args):
    if args.mode not in MODE_CHOICES:
        return 1
    elif args.mode in COMPRESS_ALIASES:
        uassetz.compress(args.i, args.o)
    elif args.mode in DECOMPRESS_ALIASES:
        uassetz.decompress(args.i, args.o)
    elif args.mode in INFORMATION_ALIASES:
        h = uassetz.read_main_header(args.i)
        args.o.write(str(h).encode("utf8"))
        args.o.write(b"\n")
    return 0


def tool_argparse(parser):
    parser.add_argument("mode", action="store", choices=MODE_CHOICES)
    parser.add_argument("i", action="store", nargs="?", type=argparse.FileType("rb"), default=sys.stdin.buffer)
    parser.add_argument("o", action="store", nargs="?", type=argparse.FileType("rb"), default=sys.stdout.buffer)
    parser.set_defaults(func=uassetztool)


def main():
    parser = argparse.ArgumentParser()
    tool_argparse(parser)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
