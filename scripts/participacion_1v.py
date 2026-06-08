#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Exporta de la BD local de la PRIMERA VUELTA 2026 (auditor.sqlite, 27 GB):
  1) participación por departamento (padrón vs votantes), y
  2) votos de Fuerza Popular (Keiko) y Juntos por el Perú (Roberto) por
     departamento, base del PRIOR de la proyección (preferencia 1V entre finalistas).
→ docs/data/participacion_1v_2026.json

La región se deriva de substr(ubigeo,1,2) (código INEI) porque la columna
`departamento` está corrupta (hallazgo Fase 1). Solo mesas estado='contabilizada'.

Nota de rendimiento: NO se selecciona la columna `raw_json` (la que infla la BD a
27 GB); SQLite no lee las overflow pages de columnas no pedidas, así que el escaneo
lee solo las columnas chicas. Aun así puede tardar algunos minutos.
"""
import sys
import json
import sqlite3
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
from regiones import ONPE_COD, norm  # noqa: E402

DB = Path("C:/Users/Lapto/Desktop/ONPE/data/auditor.sqlite")
OUT = Path(__file__).resolve().parent.parent / "docs" / "data" / "participacion_1v_2026.json"


def main():
    if not DB.exists():
        print(f"ERROR: no existe {DB}")
        sys.exit(1)

    con = sqlite3.connect(str(DB))
    con.text_factory = lambda b: b.decode("latin-1", "replace")
    cur = con.cursor()

    # ---- Pasada 1: mesas -> dep por código + participación por dep ----
    print("[1V] escaneando mesas (participación)… puede tardar")
    cod2dep = {}
    part = {}  # dep -> {habiles, votantes, mesas}
    cur.execute("SELECT codigo, ubigeo, electores_habiles, total_votantes "
                "FROM mesas WHERE estado='contabilizada'")
    n = 0
    for codigo, ubigeo, hab, vot in cur:
        n += 1
        ub = (ubigeo or "").strip()
        dep = ONPE_COD.get(ub[:2])  # None si no mapea (atípicas/extranjero)
        cod2dep[codigo] = dep
        if dep is None:
            continue
        d = part.setdefault(dep, {"habiles": 0, "votantes": 0, "mesas": 0})
        d["habiles"] += int(hab or 0)
        d["votantes"] += int(vot or 0)
        d["mesas"] += 1
    print(f"[1V] mesas contabilizadas escaneadas: {n:,} | deptos: {len(part)}")

    # ---- Pasada 2: votos_candidato -> FP/JPP por dep (prior) ----
    print("[1V] escaneando votos_candidato (FP/JPP por región)…")
    votos = {}  # dep -> {keiko, roberto}
    cur.execute("SELECT mesa_codigo, organizacion, votos FROM votos_candidato")
    m = 0
    for mesa_cod, org, v in cur:
        m += 1
        dep = cod2dep.get(mesa_cod)
        if dep is None:
            continue
        o = norm(org)
        # OJO: en la BD el nombre de JPP viene con la "Ú" mal codificada
        # ('JUNTOS POR EL PERÃ\x9a'); por eso se matchea por "JUNTOS" (sin tildes).
        if "FUERZA POPULAR" in o:
            quien = "keiko"
        elif "JUNTOS" in o:
            quien = "roberto"
        else:
            continue
        votos.setdefault(dep, {"keiko": 0, "roberto": 0})[quien] += int(v or 0)
    print(f"[1V] filas votos_candidato escaneadas: {m:,}")
    con.close()

    # ---- Armar salida ----
    nac_h = sum(d["habiles"] for d in part.values())
    nac_v = sum(d["votantes"] for d in part.values())
    regiones = []
    for dep in sorted(part):
        d = part[dep]
        vk = votos.get(dep, {}).get("keiko", 0)
        vr = votos.get(dep, {}).get("roberto", 0)
        base = vk + vr
        regiones.append({
            "region": dep,
            "habiles": d["habiles"],
            "votantes": d["votantes"],
            "participacion_pct": round(100 * d["votantes"] / d["habiles"], 2) if d["habiles"] else None,
            "mesas": d["mesas"],
            "keiko_1v_votos": vk,
            "roberto_1v_votos": vr,
            # preferencia 1V entre los DOS finalistas (prior p1_s)
            "keiko_pref_1v_pct": round(100 * vk / base, 2) if base else None,
        })

    out = {
        "meta": {
            "eleccion": "Primera vuelta 2026 (datos verificados, BD local)",
            "fuente": "auditor.sqlite (estado='contabilizada', región por ubigeo INEI)",
            "nota": "keiko_pref_1v_pct = FP/(FP+JPP) en 1V; base del swing para proyectar 2V.",
            "nacional": {
                "habiles": nac_h, "votantes": nac_v,
                "participacion_pct": round(100 * nac_v / nac_h, 2) if nac_h else None,
            },
        },
        "regiones": regiones,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"[1V] nacional participación: {out['meta']['nacional']['participacion_pct']}% "
          f"({nac_v:,}/{nac_h:,}) | {len(regiones)} regiones -> {OUT.name}")
    print("[1V] validación (deben tener sentido): top padrón")
    for x in sorted(regiones, key=lambda r: -r["habiles"])[:5]:
        print(f"   {x['region']:<16} hábiles {x['habiles']:>9,}  pref.Keiko 1V {x['keiko_pref_1v_pct']}%")


if __name__ == "__main__":
    main()
