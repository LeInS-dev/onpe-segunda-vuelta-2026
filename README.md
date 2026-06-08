# Segunda Vuelta 2026 — Proyección y monitoreo por región (datos ONPE)

Monitoreo en vivo y **proyección al 100%** de la segunda vuelta presidencial del Perú
(7 de junio de 2026): **Keiko Fujimori** (Fuerza Popular) vs **Roberto Sánchez**
(Juntos por el Perú), región por región, a partir de los datos oficiales de la ONPE.

> **Postura editorial.** Este proyecto reproduce datos oficiales de la ONPE y agrega
> una proyección estadística propia. **No afirma irregularidades ni fraude**; los
> hallazgos se presentan como observaciones. El resultado oficial y definitivo lo
> proclama el **Jurado Nacional de Elecciones (JNE)** a mediados de julio.

## Qué hace

- **Dashboard** (`docs/index.html`): mapa de predominancia por departamento, tabla
  ordenable, panel de proyección con banda de incertidumbre y gráfico de convergencia.
- **Participación** (`docs/participacion.html`): compara la participación por región
  entre la 2.ª vuelta 2026, la 1.ª vuelta 2026 y la 2.ª vuelta 2021, distinguiendo
  **tasa** de **número absoluto** de votantes.
- **Proyección estratificada por región**: en vez de extrapolar el % nacional crudo
  (sesgado porque Lima/Callao entran primero), proyecta cada región por separado y la
  pondera por su propio volumen; estima las actas faltantes con el comportamiento de
  esa región y su preferencia de 1.ª vuelta. Reporta banda 95% y escenarios.

## Fuente de datos

API oficial: `https://resultadosegundavuelta.onpe.gob.pe` (`idEleccion=10`).
El backend solo devuelve JSON ante llamadas tipo XHR; ver los headers en
[`scripts/onpe_client.py`](scripts/onpe_client.py). **No requiere navegador.**

Datos históricos (locales, no versionados aquí):
- 1.ª vuelta 2026: `auditor.sqlite` (proyecto de Fase 1).
- 2.ª vuelta 2021: CSV oficial de la PCM.

## Uso local

```bash
pip install -r requirements.txt

# 1) Capturar un corte de la ONPE y recalcular la proyección
python scripts/scrape_2v.py        # agrega un corte a docs/data/serie-2v.json
python scripts/proyeccion.py       # recalcula docs/data/proyeccion.json

# 2) Exports históricos (una sola vez; requieren los archivos de Fase 1)
python scripts/participacion_1v.py     # lee auditor.sqlite
python scripts/participacion_2021.py   # lee el CSV de la PCM

# 3) Informe PDF
python scripts/build_informe_pdf.py

# 4) Ver el dashboard
python -m http.server 8000 --directory docs   # abrir http://localhost:8000
```

## Automatización

[`.github/workflows/monitor-2v.yml`](.github/workflows/monitor-2v.yml) corre el
scraper + la proyección cada 20 min y commitea los datos.

> ⚠️ El WAF de la ONPE puede bloquear las IP de datacenter de GitHub Actions
> (devolver 403). Si eso pasa, ejecutar el scraper **localmente** en un loop y
> commitear; el dashboard se sirve igual desde GitHub Pages.

## Estructura

```
scripts/   onpe_client.py · parse_flex.py · regiones.py · scrape_2v.py
           proyeccion.py · participacion_1v.py · participacion_2021.py · build_informe_pdf.py
docs/      index.html · participacion.html · data/*.json   (GitHub Pages)
```

---
*Sitio no oficial. Datos de 2026 preliminares y sujetos a cambio.*
