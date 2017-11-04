import os
import sys
import struct
import collections

import argparse

from os.path import exists, join, relpath, isdir
from contextlib import contextmanager

from typing import Tuple, List

from . import mod
from . import uasset


MOD_APPID = "346110"
DEFAULT_MOD_STORAGE_DIR = "steamapps/workshop/content/" + MOD_APPID

# Modids here should be ignored by "install"/"remove".
# This overrides mod name if set when calling "list".
OVERRIDE_MODIDS = {
    "111111111": "Primitive+ (official)" # This is a special flower.
}


# Helper functions ###########################################################

@contextmanager
def ctxchdir(path):
    cur = os.getcwd()
    try:
        yield os.chdir(path)
    finally:
        os.chdir(cur)


def ark_platform() -> str:
    things = os.listdir("ShooterGame/Binaries")
    if "Win64" in things and "Linux" not in things:
        return "Win64"
    elif "Mac" in things and "Linux" not in things:
        return "Mac"
    return "Linux"


def is_dedicated() -> bool:
    # check for the existance of the server executable,
    # and the absence of the client executable.
    plat = ark_platform()

    if plat.startswith("Win"):
        ext = ".exe"
    else:
        ext = ""

    sv_exec = exists("ShooterGame/Binaries/" + plat + "/ShooterGameServer" + ext)
    cl_exec = exists("ShooterGame/Binaries/" + plat + "/ShooterGame" + ext)
    return sv_exec and not cl_exec


def rm(filep, verbose=False):
    if verbose:
        print("removing '%s'" % (filep))
    os.unlink(filep)


def recrm(direc, verbose=False):
    for dirpath, dirnames, filenames in os.walk(direc, topdown=False, followlinks=False):
        for dirname in dirnames:
            if verbose:
                print("removing '%s'" % filename)
            os.rmdir(dirname)
        for filename in filenames:
            if verbose:
                print("removing '%s'" % filename)
            os.unlink(filename)
    if verbose:
        print("removing '%s'" % direc)
    os.rmdir(direc)

    

#################
# CLI functions #
#################

def modtool(args):
    # Make storage dir relative to ark root
    args.mod_storage_dir = relpath(args.mod_storage_dir, args.ark_root)
    # Change to ark root dir.
    os.chdir(args.ark_root)

    # Resolve mod_platform
    # Note: ark dedicated servers seem to need the Windows versions of mod files.
    if args.mod_platform is None:
        platform = ark_platform()
        if platform == "Linux" and not is_dedicated():
            args.mod_platform = "LinuxNoEditor"
        elif platform == "Mac" and not is_dediated():
            args.mod_platform = "MacNoEditor"    # XXX: Pure guess.
        else:
            args.mod_platform = "WindowsNoEditor"

    return args.mod_func(args)

# Mod installation ###########################################################

def do_mod_install(modid: str, mod_storage_dir: str, mod_platform: str):
    storage_path = join(mod_storage_dir, modid, mod_platform)
    install_path = join(mod.MOD_LOCATION, modid)

    if exists(install_path + ".mod"):
        if not replace:
            print("Mod {0} already installed.".format(modid))
            return

    os.mkdir(install_path)

    for sdir_path, dirnames, filenames in os.walk(
        storage_path,
        followlinks=True
    ):
        idir_path = join(install_path, relpath(sdir_path, storage_path))
        
        for dirname in dirnames:
            os.mkdir(join(idir_path, dirname))
        for filename in filenames:
            if filename.endswith(".uasset.z.uncompressed_size"):
                continue
            slcidx = -2 if filename.endswith(".uasset.z") else None
            srcpath = join(sdir_path, filename)
            dstpath = join(idir_path, filename[:slcidx])
            with open(srcpath, "rb") as src, open(dstpath, "wb") as dst:
                if filename.endswith(".uasset.z"):
                    uasset.decompress(src, dst)
                else:
                    dst.write(src.read())

    mip = join(install_path, "mod.info")
    with open(mip, "rb") as mif:
        mi = mif.read()

    mmip = join(install_path, "modmeta.info")
    if exists(mmip):
        with open(mmip, "rb") as mmif:
            mmi = mmif.read()
    else:
        mmi = None

    mf = ark_gen_modfile(modid, mi, mmi)
    with open(install_path + ".mod", "wb") as modf:
        modf.write(mf)
    print("Installed {0}".format(modid))


def mod_install(args):
    if len(args.modid) == 0:
        print("No modids specified!")
        return 1

    for modid in args.modid:
        if modid in OVERRIDE_MODIDS:
            print("Ignoring special modid %s" % modid)
            continue
        do_mod_install(modid, args.mod_storage_dir, args.mod_platform)


# Mod removal ################################################################

def do_mod_remove(modid: str):
    instpath = join(mod.MOD_LOCATION, modid)
    if os.path.exists(instpath + ".mod"):
        rm(instpath + ".mod")
    if os.path.isdir(instpath):
        recrm(instpath)


def mod_remove(args):
    if len(args.modid) == 0:
        print("No modids specified!")
        return 1

    for modid in args.modid:
        if modid in OVERRIDE_MODIDS:
            print("Ignoring special modid %s" % modid)
            continue
        do_mod_remove(modid)

    return 0


# Mod upgrading ##############################################################

def do_mod_upgrade(modid: str, mod_storage_dir: str, mod_platform: str):
    pass


def mod_upgrade(args):
    if len(args.modid) == 0:
        print("No modids specified!")
        return 1

    for modid in args.modid:
        if modid in OVERRIDE_MODIDS:
            print("Ignoring special modid %s" % modid)
            continue
        do_mod_upgrade(modid)

    return 0


# Mod listing ################################################################

def mod_list(args):
    class ModEntry:
        __slots__ = ["storage_dir", "install_dir"]
        def __init__(self):
            self.storage_dir = None
            self.install_dir = None

    def modinfo_strings(path: str, statsym: str):
        if path is None:
            return " ", None
        try:
            with open(join(path, "mod.info"), "rb") as mif:
                mi = mod.ark_unpack_mod_info(mif.read())
            return statsym, mi.mod_name.decode("utf8")
        except (IOError, struct.error) as err:
            print("error: " + str(err), file=sys.stderr)
            return "!", None

    mods = collections.defaultdict(ModEntry)
    if isdir(args.mod_storage_dir):
        for modid in os.listdir(args.mod_storage_dir):
            if not modid.isnumeric():
                continue
            if len(args.modid) > 0 and modid not in args.modid:
                continue

            sdir = join(args.mod_storage_dir, modid)
            if len(os.listdir(sdir)) == 0:
                continue

            mods[modid].storage_dir = sdir

    if isdir(mod.MOD_LOCATION):
        for modid in os.listdir(mod.MOD_LOCATION):
            if not modid.isnumeric():
                continue
            if len(args.modid) > 0 and modid not in args.modid:
                continue

            mods[modid].install_dir = join(mod.MOD_LOCATION, modid)

    modids = sorted(mods.keys(), key=int)
    if len(modids) < 1:
        print("no mods to show.")
        return 0
    padding = len(modids[-1])

    for modid in modids:
        ent = mods[modid]
        # output format: [di] <modid> name (downloded, installed)
        sq, sname = modinfo_strings(ent.storage_dir, "s")
        iq, iname = modinfo_strings(ent.install_dir, "i")

        # name printing logic:
        # OVERRIDE_MODIDS? -> use that one.
        # both none? -> "(unknown)"
        # one none? -> the one that isn't.
        # both not none?
        #   are they equal? -> no choice needed.
        #   else, if not?   -> display both
        if modid in OVERRIDE_MODIDS:
            modname = OVERRIDE_MODIDS[modid]
        elif sname is None or iname is None:
            modname = sname or iname or "(unknown)"
        elif sname == iname:
            modname = iname
        else:
            modname = "installed: {0}, stored: {1}.".format(iname, sname)

        print("[{s}{i}] {mi: >{pad}} {mn}".format(
            pad=padding,
            s=sq,
            i=iq,
            mi=modid,
            mn=modname
        ))

    return 0


def tool_argparse(parser):
    parser.add_argument("-r", "--ark-root", dest="ark_root", action="store", default="./")
    parser.add_argument("-m", "--mod-storage", dest="mod_storage_dir", action="store", default=DEFAULT_MOD_STORAGE_DIR)
    parser.add_argument("-p", "--mod-platform", dest="mod_platform", action="store", choices={"LinuxNoEditor", "WindowsNoEditor"}, default=None)
    parser.set_defaults(func=modtool, mod_func=mod_list, modid=[])

    spo = parser.add_subparsers()

    lstp = spo.add_parser("list", aliases=["ls"])
    lstp.add_argument(dest="modid", action="store", nargs="*")
    lstp.set_defaults(mod_func=mod_list)

    insp = spo.add_parser("install", aliases=["ins"])
    insp.add_argument(dest="modid", action="store", nargs="*")
    insp.set_defaults(mod_func=mod_install)

    remp = spo.add_parser("remove", aliases=["rm"])
    remp.add_argument(dest="modid", action="store", nargs="*")
    remp.set_defaults(mod_func=mod_remove)

    updp = spo.add_parser("upgrade", aliases=["up"])
    updp.add_argument(dest="modid", action="store", nargs="*")
    updp.set_defaults(mod_func=mod_upgrade)


def main():
    parser = argparse.ArgumentParser()
    tool_argparse(parser)
    args = parser.parse_args()
    return args.func(args)

if __name__ == "__main__":
    sys.exit(main())
