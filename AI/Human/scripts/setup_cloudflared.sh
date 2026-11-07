#!/usr/bin/env bash
# ==============================================================================
# Setup Script for Cloudflare Tunnel (cloudflared)
# Urban Safety AI-SOC Platform
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
BIN_DIR="${PROJECT_ROOT}/bin"
CLOUDFLARED_BIN="${BIN_DIR}/cloudflared"

mkdir -p "${BIN_DIR}"

# Check if already installed in system or bin/
if command -v cloudflared &>/dev/null; then
    SYS_BIN="$(command -v cloudflared)"
    echo "✅ cloudflared is already installed at: ${SYS_BIN}"
    "${SYS_BIN}" --version
    exit 0
fi

if [[ -x "${CLOUDFLARED_BIN}" ]]; then
    echo "✅ cloudflared is already installed in project bin: ${CLOUDFLARED_BIN}"
    "${CLOUDFLARED_BIN}" --version
    exit 0
fi

echo "⬇️ Downloading official cloudflared binary for linux-amd64..."
DOWNLOAD_URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"

if command -v curl &>/dev/null; then
    curl -fsSL -o "${CLOUDFLARED_BIN}" "${DOWNLOAD_URL}"
elif command -v wget &>/dev/null; then
    wget -qO "${CLOUDFLARED_BIN}" "${DOWNLOAD_URL}"
else
    echo "❌ Error: Neither curl nor wget is available." >&2
    exit 1
fi

chmod +x "${CLOUDFLARED_BIN}"

# Attempt to install to /usr/local/bin if writable or sudo without password
if [[ -w /usr/local/bin ]]; then
    cp "${CLOUDFLARED_BIN}" /usr/local/bin/cloudflared
    echo "✅ Installed cloudflared to /usr/local/bin/cloudflared"
elif command -v sudo &>/dev/null && sudo -n true 2>/dev/null; then
    sudo cp "${CLOUDFLARED_BIN}" /usr/local/bin/cloudflared
    echo "✅ Installed cloudflared to /usr/local/bin/cloudflared via sudo"
fi

echo "✅ cloudflared installation completed successfully!"
"${CLOUDFLARED_BIN}" --version
