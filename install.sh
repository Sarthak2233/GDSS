#!/usr/bin/env bash
# ==============================================================================
# GDSS Standalone Binary Universal Installer (Linux & macOS)
# https://github.com/sarthak2233/gdss-radar
# ==============================================================================
set -euo pipefail

# ANSI color codes
BOLD='\033[1m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BOLD}${BLUE}🛰️  GDSS Standalone Installer${NC}"
echo "--------------------------------------------------"

# 1. Detect Operating System
OS="$(uname -s)"
case "${OS}" in
    Linux*)     PLATFORM="linux" ;;
    Darwin*)    PLATFORM="darwin" ;;
    *)          echo -e "${RED}Error: Unsupported operating system: ${OS}${NC}"; exit 1 ;;
esac

# 2. Detect CPU Architecture
ARCH="$(uname -m)"
case "${ARCH}" in
    x86_64|amd64)   ARCH_TARGET="amd64" ;;
    arm64|aarch64)  ARCH_TARGET="arm64" ;;
    *)              echo -e "${RED}Error: Unsupported CPU architecture: ${ARCH}${NC}"; exit 1 ;;
esac

TARGET="${PLATFORM}-${ARCH_TARGET}"
echo -e "Detected target platform: ${BOLD}${TARGET}${NC}"

# 3. Determine Latest Release Tag
REPO="sarthak2233/gdss-radar"
TAG="${GDSS_VERSION:-}"

if [ -z "${TAG}" ]; then
    echo "Resolving latest GDSS release..."
    TAG=$(curl -sSL "https://api.github.com/repos/${REPO}/releases/latest" 2>/dev/null | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/' || true)
    if [ -z "${TAG}" ]; then
        TAG="v1"
    fi
fi
echo -e "Target version: ${BOLD}${TAG}${NC}"

ARCHIVE_NAME="gdss-${TAG}-${TARGET}.tar.gz"
DOWNLOAD_URL="https://github.com/${REPO}/releases/download/${TAG}/${ARCHIVE_NAME}"
CHECKSUM_URL="https://github.com/${REPO}/releases/download/${TAG}/checksums.txt"

# 4. Create Temporary Directory
TMP_DIR=$(mktemp -d)
cleanup() {
    rm -rf "${TMP_DIR}"
}
trap cleanup EXIT

echo "Downloading ${ARCHIVE_NAME}..."
if ! curl -fsSL "${DOWNLOAD_URL}" -o "${TMP_DIR}/${ARCHIVE_NAME}"; then
    echo -e "${RED}Error: Failed to download release archive from:${NC}"
    echo "  ${DOWNLOAD_URL}"
    echo "Please check available releases at: https://github.com/${REPO}/releases"
    exit 1
fi

# 5. Verify SHA-256 Checksum (if checksums file is published)
if curl -fsSL "${CHECKSUM_URL}" -o "${TMP_DIR}/checksums.txt" 2>/dev/null; then
    echo "Verifying SHA-256 checksum..."
    cd "${TMP_DIR}"
    EXPECTED_SHA=$(grep "${ARCHIVE_NAME}" checksums.txt | awk '{print $1}' || true)
    if [ -n "${EXPECTED_SHA}" ]; then
        if command -v sha256sum >/dev/null 2>&1; then
            ACTUAL_SHA=$(sha256sum "${ARCHIVE_NAME}" | awk '{print $1}')
        elif command -v shasum >/dev/null 2>&1; then
            ACTUAL_SHA=$(shasum -a 256 "${ARCHIVE_NAME}" | awk '{print $1}')
        else
            ACTUAL_SHA=""
        fi

        if [ -n "${ACTUAL_SHA}" ]; then
            if [ "${EXPECTED_SHA}" != "${ACTUAL_SHA}" ]; then
                echo -e "${RED}Error: Checksum verification failed!${NC}"
                echo "Expected: ${EXPECTED_SHA}"
                echo "Actual:   ${ACTUAL_SHA}"
                exit 1
            fi
            echo -e "${GREEN}✓ Checksum verified.${NC}"
        fi
    fi
    cd - >/dev/null
fi

# 6. Extract Binary
echo "Extracting binary..."
tar -xzf "${TMP_DIR}/${ARCHIVE_NAME}" -C "${TMP_DIR}"

if [ ! -f "${TMP_DIR}/gdss" ]; then
    echo -e "${RED}Error: Extracted archive did not contain 'gdss' binary.${NC}"
    exit 1
fi

# 7. Determine Installation Destination
INSTALL_DIR="/usr/local/bin"
USE_SUDO=0

if [ -w "${INSTALL_DIR}" ]; then
    DEST="${INSTALL_DIR}/gdss"
elif [ -n "${SUDO_USER:-}" ] || command -v sudo >/dev/null 2>&1; then
    DEST="${INSTALL_DIR}/gdss"
    USE_SUDO=1
else
    # Fallback to user home directory
    INSTALL_DIR="${HOME}/.local/bin"
    mkdir -p "${INSTALL_DIR}"
    DEST="${INSTALL_DIR}/gdss"
fi

echo "Installing to ${DEST}..."
if [ "${USE_SUDO}" -eq 1 ]; then
    sudo mv "${TMP_DIR}/gdss" "${DEST}"
    sudo chmod +x "${DEST}"
else
    mv "${TMP_DIR}/gdss" "${DEST}"
    chmod +x "${DEST}"
fi

# 8. Check PATH
if ! echo ":${PATH}:" | grep -q ":${INSTALL_DIR}:"; then
    echo -e "${YELLOW}Warning: ${INSTALL_DIR} is not in your PATH.${NC}"
    echo "Add the following line to your ~/.bashrc, ~/.zshrc, or profile:"
    echo "  export PATH=\"${INSTALL_DIR}:\$PATH\""
fi

# 9. Verify Installation
if command -v gdss >/dev/null 2>&1; then
    echo -e "${GREEN}${BOLD}✓ GDSS successfully installed!${NC}"
else
    echo -e "${GREEN}${BOLD}✓ GDSS installed to ${DEST}${NC}"
fi

echo ""
echo -e "${BOLD}Next Steps:${NC}"
echo -e "  1. Check status:       ${BLUE}gdss status${NC}"
echo -e "  2. Compute radar:      ${BLUE}gdss tensor${NC}"
echo -e "  3. Claude Code MCP:    ${BLUE}claude mcp add gdss -- gdss mcp${NC}"
echo -e "  4. Cursor IDE MCP:     Add to ${BOLD}~/.cursor/mcp.json${NC}:"
echo -e "     {"
echo -e "       \"mcpServers\": {"
echo -e "         \"gdss\": { \"command\": \"gdss\", \"args\": [\"mcp\"] }"
echo -e "       }"
echo -e "     }"
