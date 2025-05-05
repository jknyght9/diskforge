#!/bin/bash

find examples/ -type f -iname "*.img" -exec rm {} \;

docker build -t diskbuilder .

for scenario in example_gpt example_mbr example_luks example_veracrypt; do
#for scenario in example_veracrypt; do
  echo "[*] Running: $scenario"
  docker run --rm --privileged \
    -v "$(pwd)/examples/$scenario:/output" \
    -v "$(pwd)/examples/$scenario/manifest.json:/manifests/manifest.json" \
    -v "$(pwd)/files:/files" \
    diskbuilder /manifests/manifest.json
done
