import sys

import argparse

from . import modtool


    

def main():
    parser = argparse.ArgumentParser()

    def usage(_):
        parser.print_help()
        return 1

    parser.set_defaults(func=usage)
    spo = parser.add_subparsers()
    modp = spo.add_parser("mod")
    modtool.tool_argparse(modp)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
