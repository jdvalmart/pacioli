#!/bin/bash
# Desinstalador de Pacioli
set -e

echo "Desinstalando Pacioli..."

sudo rm -f /usr/local/bin/pacioli
sudo rm -f /usr/share/applications/pacioli.desktop
sudo update-desktop-database /usr/share/applications/ 2>/dev/null || true

echo "✓ Pacioli desinstalado"
