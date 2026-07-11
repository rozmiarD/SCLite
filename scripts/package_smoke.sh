#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
REPO_ROOT="$(pwd)"

if [ -n "${PYTHON:-}" ]; then
  PYTHON_BIN="${PYTHON}"
elif [ -x ".venv/bin/python" ]; then
  PYTHON_BIN=".venv/bin/python"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
else
  echo "python interpreter not found; set PYTHON=/path/to/python" >&2
  exit 127
fi

TMPDIR_ROOT="$(mktemp -d)"
GENERATED_REPO_PATHS=(build dist sclite_core.egg-info)
for path in "${GENERATED_REPO_PATHS[@]}"; do
  if [ -e "${path}" ]; then
    echo "refusing to run package smoke with existing build artifact: ${path}" >&2
    exit 1
  fi
done

cleanup() {
  rm -rf "${TMPDIR_ROOT}"
  for path in "${GENERATED_REPO_PATHS[@]}"; do
    rm -rf "${REPO_ROOT}/${path}"
  done
}
trap cleanup EXIT

"${PYTHON_BIN}" -m venv "${TMPDIR_ROOT}/build-venv"
BUILD_PY="${TMPDIR_ROOT}/build-venv/bin/python"
"${BUILD_PY}" -m pip install -r "${REPO_ROOT}/.github/release-build-requirements.txt" >/dev/null
"${BUILD_PY}" -m build --outdir "${TMPDIR_ROOT}/dist"
scripts/normalize_sdist.sh "${TMPDIR_ROOT}"/dist/*.tar.gz
"${BUILD_PY}" -m twine check "${TMPDIR_ROOT}"/dist/*

"${PYTHON_BIN}" -m venv "${TMPDIR_ROOT}/install-venv"
INSTALL_PY="${TMPDIR_ROOT}/install-venv/bin/python"
"${INSTALL_PY}" -m pip install pip==26.1.2 >/dev/null
"${INSTALL_PY}" -m pip install "${TMPDIR_ROOT}"/dist/*.whl >/dev/null
"${INSTALL_PY}" -m pip check

"${PYTHON_BIN}" -m venv "${TMPDIR_ROOT}/sdist-install-venv"
SDIST_INSTALL_PY="${TMPDIR_ROOT}/sdist-install-venv/bin/python"
"${SDIST_INSTALL_PY}" -m pip install pip==26.1.2 >/dev/null
"${SDIST_INSTALL_PY}" -m pip install "${TMPDIR_ROOT}"/dist/*.tar.gz >/dev/null
"${SDIST_INSTALL_PY}" -m pip check
"${SDIST_INSTALL_PY}" -c "import importlib.metadata as md, sclite; assert md.version('sclite-core') == sclite.__version__"

cd "${TMPDIR_ROOT}"
"${INSTALL_PY}" - <<'PY'
import importlib.metadata
import sclite

assert importlib.metadata.version('sclite-core') == sclite.__version__
assert hasattr(sclite, 'verify_lifecycle_manifest')
assert hasattr(sclite, 'verify_secure_bundle')
print(f"sclite_package_smoke_ok:{sclite.__version__}")
PY
