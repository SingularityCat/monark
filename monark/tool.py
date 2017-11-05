import sys

import argparse

from . import modtool
from . import uassetztool


    

def main():
    parser = argparse.ArgumentParser()

    def usage(_):
        parser.print_help()
        return 1

    parser.set_defaults(func=usage)
    spo = parser.add_subparsers()
    modp = spo.add_parser("mod")
    modtool.tool_argparse(modp)
    uztp = spo.add_parser("uassetz")
    uassetztool.tool_argparse(uztp)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
