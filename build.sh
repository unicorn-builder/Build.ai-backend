#!/usr/bin/env bash
# Render build script — installs ODA File Converter + Python deps

set -e

# Python dependencies
pip install -r requirements.txt

# ODA File Converter for DWG↔DXF conversion (free, headless)
if ! command -v ODAFileConverter &> /dev/null; then
    echo "Installing ODA File Converter..."
    apt-get update -qq && apt-get install -y -qq libgl1 libglib2.0-0 libxkbcommon0 || true
    curl -sL "https://dl.opendesign.com/guestfiles/Demo/ODAFileConverter_QT6_lnxX64_8.3dll_25.12.deb" -o /tmp/oda.deb || true
    dpkg -i /tmp/oda.deb 2>/dev/null || apt-get install -f -y -qq 2>/dev/null || true
    rm -f /tmp/oda.deb
    echo "ODA File Converter installed: $(which ODAFileConverter 2>/dev/null || echo 'not found')"
else
    echo "ODA File Converter already installed"
fi
