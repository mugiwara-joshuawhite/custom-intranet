#!/bin/bash
# Use this so that you don't have to type this whole thing out every time you run the Docker container :3
# Works in Linux shell
# I also haven't tested this because I am unfortunately on Windows currently, so let me know if it doesn't work.
docker run --rm -it --privileged --network none -v "$PWD":/work cs4220-net