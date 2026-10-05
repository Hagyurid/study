#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/models/DepthAnythingV2SmallF16P6.mlpackage"
mkdir -p "$ROOT/models"
rm -rf "$DEST"
python3 -m pip install -q "huggingface_hub[cli]"
python3 - <<'PY'
from huggingface_hub import snapshot_download
snapshot_download(repo_id="apple/coreml-depth-anything-v2-small",local_dir="models-hf",allow_patterns=["DepthAnythingV2SmallF16P6.mlpackage/*"])
PY
mv models-hf/DepthAnythingV2SmallF16P6.mlpackage "$DEST"
rm -rf models-hf
echo "Model ready: $DEST"
