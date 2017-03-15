#!/usr/bin/env bash

set -e

# Generate README.rst from README.md (useful to publish on PyPi)
pandoc --from=markdown --to=rst --output=README.rst README.md

# Remove old builds
rm -rf dist/*

# Build from setup.py
python3 setup.py bdist_wheel
