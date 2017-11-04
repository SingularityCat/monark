#!/usr/bin/env python3
from setuptools import setup

setup(
    name = "monark",
    version = "0.0.0",
    author = "Elliot Thomas",
    author_email = "e.singularitycat@gmail.com",
    description = "MonARK - took for manipulating an 'ARK: Survival Evolved' installation.",
    classifiers = [
        "Environment :: Console",
        "Topic :: Utilities",
        "Programming Language :: Python :: 3",
        "Natural Language :: English",
        "Development Status :: 3 - Alpha"
    ],
    packages=["monark"],
    scripts=["bin/monark"],
)

