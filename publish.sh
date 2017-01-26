#!/usr/bin/env bash

# Build
./build.sh

# Push on PyPi
twine upload dist/*
