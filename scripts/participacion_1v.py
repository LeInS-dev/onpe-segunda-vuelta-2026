#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Exporta de la BD local de la PRIMERA VUELTA 2026 (auditor.sqlite, 27 GB):
  1) participación por departamento (padrón vs votantes), y
  2) preferencia Keiko = FP/(FP+JPP) por departamento (PRIOR de la proyección).
→ docs/data/participacion_1v_2026.json

OJO — coherencia de regiones: la BD agrupa bien las mesas por el prefijo de 2
dígitos de `ubigeo`, pero los NOMBRES de departamento que trae están desordenados
(corrupción "colegios desplazados" de Fase 1). Por eso NO se confía ni en la columna
`departamento` ni en un mapa de códigos fijo: se asigna cada código de la BD al
departamento de la API oficial de 2ª vuelta cuyo número de mesas coincide (mismas
mesas físicas entre vueltas), y se VALIDA cada región contra el padrón de 2021.
Las regiones que no validan se marcan no confiables (participación = null).

Solo mesas estado='contabilizada'. NO se selecciona `raw_json` (la BD pesa 27 GB
por esa columna; SQLite no lee sus overflow pages si no se pide).
"""
import sys
import json
import sqlite3
from pathlib import Path
from collections import defaultdict

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
from regiones import canon_region, norm  # noqa: E402

DB = Path("C:/Users/Lapto/Desktop/ONPE/data/auditor.sqlite")
DATA = Path(__file__).resolve().parent.parent / "docs" / "data"
OUT = DATA / "participacion_1v_2026.json"

VALID_LO, VALID_HI = 0.85, 1.40  # ratio padrón 1V2026 / 2V2021 aceptable


def main():
    if not DB.exists():
        print(f"ERROR: no existe {DB}")
        sys.exit(1)

    # ---- referencias autoritativas (nombres correctos) ----
    serie = json.loads((DATA / "serie-2v.json").read_text(encoding="utf-8"))
    reg2v = {}  # canon -> {nombre, actas, keiko2v}
    for r in serie["cortes"][-1]["regiones"]:
        reg2v[canon_region(r["region"])] = {"nombre": r["region"], "actas": r["actas_total"],
                                             "keiko2v": r.get("keiko_pct")}
    p21 = json.loads((DATA / "participacion_2v_2021.json").read_text(encoding="utf-8"))
    hab21 = {canon_region(r["region"]): r["habiles"] for r in p21["regiones"]}

    # ---- escaneo de la BD, agregando por CÓDIGO (prefijo ubigeo, sin nombrar) ----
    con = sqlite3.connect(str(DB))
    con.text_factory = lambda b: b.decode("latin-1", "replace")
    cur = con.cursor()
    print("[1V] escaneando mesas (por código de ubigeo)… puede tardar")
    percode = defaultdict(lambda: {"hab": 0, "vot": 0, "mesas": 0})
    cod_de = {}  # codigo_mesa -> code(2 díg)
    cur.execute("SELECT codigo, ubigeo, electores_habiles, total_votantes "
                "FROM mesas WHERE estado='contabilizada'")
    n = 0
    for codigo, ubigeo, hab, vot in cur:
        n += 1
        code = (ubigeo or "")[:2]
        cod_de[codigo] = code
        d = percode[code]
        d["hab"] += int(hab or 0)
        d["vot"] += int(vot or 0)
        d["mesas"] += 1
    print(f"[1V] mesas contabilizadas: {n:,} | códigos: {len(percode)}")

    print("[1V] escaneando votos_candidato (FP/JPP por código)…")
    votes = defaultdict(lambda: {"keiko": 0, "roberto": 0})
    cur.execute("SELECT mesa_codigo, organizacion, votos FROM votos_candidato")
    for mesa_cod, org, v in cur:
        code = cod_de.get(mesa_cod)
        if code is None:
            continue
        o = norm(org)
        if "FUERZA POPULAR" in o:
            votes[code]["keiko"] += int(v or 0)
        elif "JUNTOS" in o:  # 'JUNTOS POR EL PERÚ' viene con la Ú mal codificada
            votes[code]["roberto"] += int(v or 0)
    con.close()

    # ---- asignación código -> departamento ----
    # Señal principal: el patrón político (la preferencia Keiko de 1V de un código debe
    # parecerse al % Keiko de 2V de su región, salvo el swing). Señal secundaria: el nº
    # de mesas. Coste combinado = |pref1V − keiko2V| + 0.003·|mesas − actas2V|.
    def pref(code):
        vk, vr = votes[code]["keiko"], votes[code]["roberto"]
        return (100 * vk / (vk + vr)) if (vk + vr) else None
    codes = [(c, percode[c]["mesas"], pref(c)) for c in percode if c.isdigit() and 1 <= int(c) <= 25]
    regions = [(k, v["actas"], v["keiko2v"]) for k, v in reg2v.items()
               if k != "EXTRANJERO" and v["keiko2v"] is not None]
    pares = []
    for c, m, pr in codes:
        if pr is None:
            continue
        for name, a, k2 in regions:
            pares.append((abs(pr - k2) + 0.003 * abs(m - a), c, name))
    pares.sort()
    code2name, name2code = {}, {}
    for _, c, name in pares:
        if c in code2name or name in name2code:
            continue
        code2name[c] = name
        name2code[name] = c

    # ---- construir salida por región, con validación ----
    regiones = []
    nac_h = nac_v = 0
    for code, name in sorted(code2name.items(), key=lambda x: x[1]):
        d = percode[code]
        vk = votes[code]["keiko"]
        vr = votes[code]["roberto"]
        base = vk + vr
        h21 = hab21.get(name, 0)
        ratio = d["hab"] / h21 if h21 else 0
        pr = (100 * vk / base) if base else None
        k2 = reg2v.get(name, {}).get("keiko2v")
        swing = (pr - k2) if (pr is not None and k2 is not None) else None
        # confiable si el padrón cuadra con 2021 Y el swing 1V→2V es plausible (0–28 pp)
        confiable = bool(h21 and VALID_LO <= ratio <= VALID_HI
                         and swing is not None and 0 <= swing <= 28)
        nac_h += d["hab"]
        nac_v += d["vot"]
        regiones.append({
            "region": name,
            "confiable": confiable,
            "habiles": d["hab"] if confiable else None,
            "votantes": d["vot"] if confiable else None,
            "participacion_pct": (round(100 * d["vot"] / d["hab"], 2) if confiable and d["hab"] else None),
            "mesas": d["mesas"],
            "keiko_1v_votos": vk if confiable else None,
            "roberto_1v_votos": vr if confiable else None,
            "keiko_pref_1v_pct": (round(100 * vk / base, 2) if confiable and base else None),
            "_ratio_padron": round(ratio, 2),
        })

    out = {
        "meta": {
            "eleccion": "Primera vuelta 2026 (BD local, regiones remapeadas por nº de mesas vs API 2V)",
            "fuente": "auditor.sqlite (estado='contabilizada')",
            "nota": ("Regiones asignadas por coincidencia de nº de mesas con la API oficial de 2ª "
                     "vuelta y validadas contra el padrón 2021; las no confiables van con participación null. "
                     "keiko_pref_1v_pct = FP/(FP+JPP), prior del swing."),
            "nacional": {
                "habiles_mapeado": nac_h, "votantes_mapeado": nac_v,
                "participacion_pct": round(100 * nac_v / nac_h, 2) if nac_h else None,
            },
        },
        "regiones": regiones,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    conf = [r for r in regiones if r["confiable"]]
    print(f"[1V] regiones confiables: {len(conf)}/{len(regiones)} | participación nac (mapeada): "
          f"{out['meta']['nacional']['participacion_pct']}%")
    print("[1V] NO confiables (participación n/d):",
          ", ".join(f"{r['region']}({r['_ratio_padron']})" for r in regiones if not r["confiable"]) or "ninguna")
    print("[1V] muestra confiables:")
    for r in sorted(conf, key=lambda r: -r["habiles"])[:6]:
        print(f"   {r['region']:<14} part {r['participacion_pct']}% · pref.Keiko1V {r['keiko_pref_1v_pct']}% · mesas {r['mesas']}")


if __name__ == "__main__":
    main()
