#!/bin/sh
# Copies the shared script into each skill and rebuilds the zip packages for Copilot Studio.
set -e
cd "$(dirname "$0")/.."
for skill in slm-data-extraction slm-thematic-analysis slm-research-type; do
  cp tools/slm_extract.py "$skill/scripts/slm_extract.py"
  rm -f "dist/$skill.zip"
  (cd "$skill" && zip -qr "../dist/$skill.zip" SKILL.md references scripts -x '*__pycache__*')
done
echo "Skills packaged in dist/"
