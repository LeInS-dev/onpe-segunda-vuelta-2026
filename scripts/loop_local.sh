#!/usr/bin/env bash
# Loop de captura LOCAL cada 20 min para la Segunda Vuelta 2026.
# Captura un corte de la ONPE, recalcula la proyección y publica los datos.
# Uso:  bash scripts/loop_local.sh [segundos]   (por defecto 1200 = 20 min)
# Cortar con Ctrl+C. Dejar corriendo mientras dure el escrutinio.
set -u
cd "$(dirname "$0")/.."
INTERVALO="${1:-1200}"
echo "[loop] iniciado · intervalo ${INTERVALO}s · Ctrl+C para detener"
while true; do
  echo "[loop] $(date '+%Y-%m-%d %H:%M:%S') capturando…"
  python scripts/scrape_2v.py || echo "[loop] scrape falló (reintenta al próximo ciclo)"
  python scripts/proyeccion.py || echo "[loop] proyección falló"
  git add docs/data/serie-2v.json docs/data/proyeccion.json
  if git diff --staged --quiet; then
    echo "[loop] sin cambios; no se publica."
  else
    git commit -q -m "datos: corte local $(date -u +'%Y-%m-%dT%H:%MZ')" && git push -q \
      && echo "[loop] publicado ✓" || echo "[loop] commit/push falló"
  fi
  sleep "$INTERVALO"
done
