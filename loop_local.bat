@echo off
REM Loop de captura LOCAL cada 20 min para la Segunda Vuelta 2026 (Windows).
REM Doble clic para iniciar. Cerrar la ventana para detener.
cd /d "%~dp0"
:loop
echo [loop] %date% %time% capturando...
python scripts\scrape_2v.py
python scripts\proyeccion.py
git add docs\data\serie-2v.json docs\data\proyeccion.json
git diff --staged --quiet || (git commit -m "datos: corte local %date% %time%" && git push)
echo [loop] esperando 20 min...
timeout /t 1200 /nobreak >nul
goto loop
