#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Exporta la participación de la SEGUNDA VUELTA 2021 por departamento, desde el CSV
oficial de la PCM (local), a docs/data/participacion_2v_2021.json.

Fuente: ONPE/data/eg2021/Resultados_2da_vuelta_Version_PCM .csv (latin-1, ';').
Columnas usadas: UBIGEO, DEPARTAMENTO, N_CVAS (votantes), N_ELEC_HABIL (padrón).
Verificado: agrega a 74,57% nacional (coincide con el 74,56% de la prensa).
"""
import sys
import csv
import json
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
from regiones import canon_region  # noqa: E402

CSV_2021 = Path("C:/Users/Lapto/Desktop/ONPE/data/eg2021/Resultados_2da_vuelta_Version_PCM .csv")
OUT = Path(__file__).resolve().parent.parent / "docs" / "data" / "participacion_2v_2021.json"


def to_int(x):
    try:
        return int(str(x).strip() or 0)
    except ValueError:
        return 0


def main():
    if not CSV_2021.exists():
        print(f"ERROR: no existe {CSV_2021}")
        sys.exit(1)

    acc = {}  # region -> {habiles, votantes}
    nac_h = nac_v = 0
    with CSV_2021.open(encoding="latin-1", newline="") as f:
        r = csv.DictReader(f, delimiter=";")
        for row in r:
            # clave por DEPARTAMENTO; el extranjero llega como continentes
            reg = canon_region(row.get("DEPARTAMENTO"))
            if reg is None:
                continue
            h = to_int(row.get("N_ELEC_HABIL"))
            v = to_int(row.get("N_CVAS"))
            d = acc.setdefault(reg, {"habiles": 0, "votantes": 0})
            d["habiles"] += h
            d["votantes"] += v
            nac_h += h
            nac_v += v

    regiones = []
    for reg, d in sorted(acc.items()):
        part = round(100 * d["votantes"] / d["habiles"], 2) if d["habiles"] else None
        regiones.append({"region": reg, "habiles": d["habiles"],
                         "votantes": d["votantes"], "participacion_pct": part})

    out = {
        "meta": {
            "eleccion": "Segunda vuelta 2021",
            "fuente": "ONPE / PCM (Resultados_2da_vuelta_Version_PCM)",
            "nacional": {
                "habiles": nac_h, "votantes": nac_v,
                "participacion_pct": round(100 * nac_v / nac_h, 2) if nac_h else None,
            },
        },
        "regiones": regiones,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[2021] nacional: {out['meta']['nacional']['participacion_pct']}% "
          f"({nac_v:,}/{nac_h:,}) | {len(regiones)} regiones -> {OUT.name}")
    for x in sorted(regiones, key=lambda r: -(r['participacion_pct'] or 0))[:6]:
        print(f"   {x['region']:<16} {x['participacion_pct']}%")


if __name__ == "__main__":
    main()
