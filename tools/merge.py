#!/usr/bin/python3
import argparse

import os
import re
import configparser
import difflib
import shutil

def newlines(n):
    while n > 0:
        yield "\n"
        n -= 1

def update_cfg_stream(settings, source):
    section = None
    setkeys = set()
    seckeys = set()
    nlcount = 0
    for line in source:
        l = line.strip()
        # Defer newline reproduction so that new keys can be added before them.
        if l == "":
            nlcount += 1
            continue

        if l.startswith("[") and l.endswith("]"):
            if section is not None:
                # append all remaining keys to current section
                for key in settings[section].keys() - setkeys:
                    yield "{0}={1}\n".format(key, settings[section][key])
            setkeys.clear()
            yield from newlines(nlcount)
            yield line
            nlcount = 0
            section = l[l.find("[") + 1:l.rfind("]")]
            seckeys.add(section)
            if section not in settings:
                section = None  # skip it.
            continue

        if section is not None:
            rem = re.match("(^[A-z0-9_]* *= *)", l)
            if rem is not None:
                key = l.partition("=")[0].strip()
                if key in settings[section]:
                    setkeys.add(key)
                    yield from newlines(nlcount)
                    yield rem.groups()[0] + settings[section][key] + "\n"
                    nlcount = 0
                    continue
        yield from newlines(nlcount)
        yield line
        nlcount = 0
    yield from newlines(nlcount)
    for section in settings.keys() - seckeys:
        yield "[{0}]\n".format(section)
        for key, value in settings[section].items():
            yield "{0}={1}\n".format(key, value)
        yield "\n"


parser = argparse.ArgumentParser()
parser.add_argument("-c", "--confpath", dest="conf_path", action="store", default="../ShooterGame/Saved/Config/LinuxServer/")
parser.add_argument("-m", "--mergepath", dest="merge_path", action="store", default="./")
parser.add_argument("-i", "--interactive", dest="interactive", action="store_true", default=False)
parser.add_argument("-d", "--dry", dest="dry", action="store_true", default=False)

args = parser.parse_args()


for conf in os.listdir(args.merge_path):
    if not conf.endswith(".ini"):
        continue

    if not os.path.exists(args.conf_path + conf):
        print("=== copying", conf)
        src, dest = args.merge_path + conf, args.conf_path + conf
        if args.dry:
            continue
        if args.interactive:
            resp = input("copy '%s' to '%s'? [y/n] " % (src, dest)).lower()
            if not resp.startswith("y"):
                continue
        shutil.copy(src, dest)
        continue

    print("=== merging", conf)
    mrgcfg = configparser.ConfigParser()
    mrgcfg.optionxform = lambda option: option

    with open(args.merge_path + conf, "rt") as source:
        mrgcfg.read_file(source)

    with open(args.conf_path + conf, "rt") as source:
        oldcfg = source.readlines()

    mrgcfg = dict(mrgcfg)
    del mrgcfg["DEFAULT"]
    newcfg = list(update_cfg_stream(mrgcfg, oldcfg))

    print("=== diff")
    print("".join(difflib.unified_diff(oldcfg, newcfg)))
    print("=== diff end")
    if args.dry:
        continue
    if args.interactive:
        resp = input("update '%s'? [y/n]" % (conf)).lower()
        if not resp.startswith("y"):
            continue

    with open(args.conf_path + conf + ".atom", "wt") as newfile:
        newfile.writelines(newcfg)

    os.rename(args.conf_path + conf, args.conf_path + conf + ".orig")
    os.rename(args.conf_path + conf + ".atom", args.conf_path + conf)
