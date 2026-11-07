#!/bin/sh
# Rebuilds every brand asset, then the preview sheets.
#   sh build.sh
#   1. mark.py       parameters -> geometry.json
#   2. export.swift  geometry.json + wordmark.json -> ../svg, ../export (flattened SVG, PNG, ICO, manifests)
#   3. headless Chrome renders preview.html and vs-board.html -> ../preview
set -eu
here=$(cd "$(dirname "$0")" && pwd)
out="$here/../preview"
chrome="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"

python3 "$here/mark.py"
swift "$here/export.swift"
if [ ! -x "$chrome" ]; then echo "Chrome not found (set CHROME=...); skipped the previews"; exit 0; fi
mkdir -p "$out"
render() { # page width height output
  "$chrome" --headless=new --disable-gpu --hide-scrollbars --allow-file-access-from-files \
    --window-size="$2,$3" --screenshot="$out/$4" "file://$here/$1" 2>/dev/null
}
render preview.html 1600 1640 overview.png
render vs-board.html 1800 600 vs-board.png
echo "previews in $(cd "$out" && pwd)"
