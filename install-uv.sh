#! /bin/bash

set -o errexit
set -o xtrace

echo "Run install uv"

IS_UV_INSTALL=$(python3 -m pip show uv 2>/dev/null || true)
UV_VER="0.6.6"

echo "Check if uv is installed"
if [ -z "${IS_UV_INSTALL}" ]; then
    echo "uv is not installed. Installing..."
    python3 -m pip install uv=="${UV_VER}"
else
    echo "uv is already installed. Skips"
    python3 -m pip show uv
fi