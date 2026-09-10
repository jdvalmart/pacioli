#!/bin/bash
# Instalador de Pacioli para Fedora/Linux
set -e

echo "Instalando Pacioli..."

# Copiar ejecutable
sudo cp dist/Pacioli /usr/local/bin/pacioli
sudo chmod +x /usr/local/bin/pacioli

# Copiar desktop file
sudo cp pacioli.desktop /usr/share/applications/pacioli.desktop

# Actualizar base de datos de iconos
sudo update-desktop-database /usr/share/applications/ 2>/dev/null || true

echo ""
echo "✓ Pacioli instalado correctamente"
echo "  Ejecutar: pacioli"
echo "  O buscarlo en el menú de aplicaciones"
