#!/usr/bin/env python3

VERSION = "0.0.6"

DESCRIPTION = "Python module for simple pattern matching"
CLASSIFIERS = [
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Natural Language :: English",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3",
    "Topic :: Software Development :: Libraries :: Python Modules",
]


def main():
    try:
        from setuptools import setup
    except ImportError:
        from distutils.core import setup

    with open("README.md") as fin:
        desc = fin.read().strip()

    options = {
        "name": "py-ttern",
        "version": VERSION,
        "license": "MIT",
        "description": DESCRIPTION,
        "long_description": desc,
        "long_description_content_type": "text/markdown",
        "url": "https://github.com/Z-Shang/pyttern",
        "author": "zshang",
        "author_email": "z@gilgamesh.me",
        "classifiers": CLASSIFIERS,
        "packages": [
            "pyttern",
        ],
        "install_requires": ["bytecode", "fppy"],
    }
    setup(**options)


if __name__ == "__main__":
    main()
