#!/usr/bin/env bash
set -euo pipefail

python -m PyInstaller --onefile --windowed --name FAANGTrail --paths src --add-data "src/faangtrail/data:faangtrail/data" --clean faangtrail_entry.py
ditto -c -k --keepParent dist/FAANGTrail dist/FAANGTrail-macos.zip
printf 'Built dist/FAANGTrail-macos.zip\n'