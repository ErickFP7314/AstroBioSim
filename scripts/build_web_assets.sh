#!/usr/bin/env bash
# Regenera los assets que Pyodide carga en el navegador: el wheel del paquete y
# los CSV de datos, dentro de frontend/public/pyodide/. Correr tras cambiar código
# Python del motor, y commitear el resultado (Cloudflare Pages no corre Python).
set -euo pipefail
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
PY="${PYTHON:-$RAIZ/.venv/bin/python}"
DEST="$RAIZ/frontend/public/pyodide"
mkdir -p "$DEST/data"
rm -f "$DEST"/*.whl
"$PY" -m pip wheel "$RAIZ" --no-deps -w "$DEST"
cp "$RAIZ/data/processed/datos_tierra_control_2025.csv" \
   "$RAIZ/data/processed/datos_atacama_2025_EXTREMOS_REALES.csv" \
   "$RAIZ/data/processed/datos_ventilas_2025_procesados.csv" "$DEST/data/"
echo "Assets web regenerados en $DEST"
