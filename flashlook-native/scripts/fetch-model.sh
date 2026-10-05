#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
MODEL="DepthAnythingV2SmallF16P6.mlpackage"
DEST="models/$MODEL"
mkdir -p models
if [ -d "$DEST" ]; then echo "Core ML model already present"; exit 0; fi
python3 -m pip install -q --disable-pip-version-check huggingface_hub
python3 - <<'PY'
from huggingface_hub import snapshot_download
snapshot_download(
 repo_id="apple/coreml-depth-anything-v2-small",
 local_dir="models",
 allow_patterns=["DepthAnythingV2SmallF16P6.mlpackage/*"]
)
PY
test -f "$DEST/Manifest.json"
test -f "$DEST/Data/com.apple.CoreML/model.mlmodel"
echo "Core ML model ready: $DEST"
