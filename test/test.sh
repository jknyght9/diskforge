#!/bin/bash
set -euo pipefail

find examples/ -type f -iname "*.img" -exec rm {} \;

docker build -t diskforge .

echo ""
echo "============================================"
echo " PHASE 1: BUILD"
echo "============================================"
echo ""

for scenario in example_gpt example_mbr example_luks example_veracrypt example_raw example_template example_btrfs example_f2fs example_inject; do
  echo "[*] Building: $scenario"
  docker run --rm --privileged \
    -v "$(pwd)/examples/$scenario:/output" \
    -v "$(pwd)/examples/$scenario/manifest.json:/manifests/manifest.json" \
    -v "$(pwd)/files:/files" \
    diskforge /manifests/manifest.json
done

echo ""
echo "============================================"
echo " PHASE 2: VERIFY"
echo "============================================"
echo ""

docker run --rm --privileged \
  -v "$(pwd)/examples/example_gpt:/output/example_gpt" \
  -v "$(pwd)/examples/example_mbr:/output/example_mbr" \
  -v "$(pwd)/examples/example_luks:/output/example_luks" \
  -v "$(pwd)/examples/example_veracrypt:/output/example_veracrypt" \
  -v "$(pwd)/examples/example_raw:/output/example_raw" \
  -v "$(pwd)/examples/example_template:/output/example_template" \
  -v "$(pwd)/examples/example_btrfs:/output/example_btrfs" \
  -v "$(pwd)/examples/example_f2fs:/output/example_f2fs" \
  -v "$(pwd)/examples/example_inject:/output/example_inject" \
  -v "$(pwd)/test/verify.sh:/verify.sh" \
  --entrypoint bash \
  diskforge /verify.sh
