#!/usr/bin/env bash
# Install LibreOffice
apt-get update
apt-get install -y libreoffice

# Install Python dependencies
pip install -r requirements.txt
