#!/bin/sh
# Build plugin.video.myyoutubers-<version>.zip from this repository.
set -e
cd "$(dirname "$0")"

ADDON_ID="plugin.video.myyoutubers"
VERSION="$(grep -m1 'id="plugin.video.myyoutubers"' addon.xml | sed 's/.*version="\([0-9.]*\)".*/\1/')"

if [ -z "$VERSION" ]; then
    echo "error: could not read version from addon.xml" >&2
    exit 1
fi

OUT="${ADDON_ID}-${VERSION}.zip"
rm -f "$OUT"

python3 - "$OUT" "$ADDON_ID" <<'PYEOF'
import os
import sys
import zipfile

out, addon_id = sys.argv[1], sys.argv[2]

EXCLUDE_DIRS = {"__pycache__", ".git"}
EXCLUDE_FILES = {
    "build.sh",
    ".gitignore",
    ".gitattributes",
    "README.md",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
}

with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for f in sorted(files):
            if f in EXCLUDE_FILES or f.endswith(".pyc") or f.endswith(".zip"):
                continue
            full = os.path.join(root, f)
            rel = os.path.relpath(full, ".")
            z.write(full, os.path.join(addon_id, rel))
    print("  entries: %d" % len(z.infolist()))
PYEOF

echo "Built: ${OUT}"
