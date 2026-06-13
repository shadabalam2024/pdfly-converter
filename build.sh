#!/usr/bin/env bash
set -e

# Install LibreOffice
apt-get update -y
apt-get install -y libreoffice libreoffice-writer

# Install Python dependencies
pip install -r requirements.txt
