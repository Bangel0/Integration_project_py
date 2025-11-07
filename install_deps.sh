!/usr/bin/env bash
# set -euo pipefail

echo "[uv] Comprobando dependencias…"

if [[ -f "requirements.txt" ]]; then
  echo "[uv] Se encontró requirements.txt — instalando con: uv pip install -r requirements.txt"
  uv add -r requirements.txt

else
  echo "[uv] No se instalaron dependencias: no se encontró ni pyproject.toml ni requirements.txt"
fi

# if [[ -f "pyproject.toml" ]]; then
#   echo "[uv] Se encontró pyproject.toml"

#   if [[ -f "uv.lock" ]]; then
#     echo "[uv] Se encontró uv.lock — instalando con: uv sync --frozen"
#     uv sync --frozen
#   else
#     echo "[uv] No hay uv.lock — instalando con: uv sync"
#     uv sync
#   fi

# elif [[ -f "requirements.txt" ]]; then
#   echo "[uv] Se encontró requirements.txt — instalando con: uv pip install -r requirements.txt"
#   uv pip install -r requirements.txt

# else
#   echo "[uv] No se instalaron dependencias: no se encontró ni pyproject.toml ni requirements.txt"
# fi