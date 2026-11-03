#!/usr/bin/env bash
# Zip extension/ for the GitHub release and the Chrome Web Store: dist/middle-frame.zip (+ a versioned copy).
set -euo pipefail
cd "$(dirname "$0")/.."
ver=$(python3 -c "import json; print(json.load(open('extension/manifest.json'))['version'])")
mkdir -p dist
rm -f dist/middle-frame.zip
(cd extension && zip -qr -X ../dist/middle-frame.zip . -x '.*')
cp dist/middle-frame.zip "dist/middle-frame-$ver.zip"
unzip -l dist/middle-frame.zip
echo "-> dist/middle-frame.zip (v$ver)"
