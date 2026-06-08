#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Captura un corte de la Segunda Vuelta 2026 desde la API oficial de la ONPE y
lo agrega a docs/data/serie-2v.json.

Un "corte" = nacional (sumado de regiones) + 25 departamentos + extranjero, con:
  · % de actas, actas totales/contabilizadas/pendientes
  · votos válidos y % de Keiko (FP) y Roberto (JPP)
  · líder de la región

Pensado para correr cada ~20 min (GitHub Actions) o manualmente.
Sin dependencias de navegador: usa requests + headers XHR (ver onpe_client.py).

Uso:
  python scripts/scrape_2v.py            # consulta y agrega un corte
  python scripts/scrape_2v.py --dry-run  # consulta y muestra, no escribe
"""
import sys
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

# La consola de Windows (cp1252) no imprime tildes ni símbolos como →; forzar UTF-8.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
from onpe_client import OnpeClient            # noqa: E402
from parse_flex import extraer_candidatos, pct_sobre_dos  # noqa: E402

DATA_PATH = Path(__file__).resolve().parent.parent / "docs" / "data" / "serie-2v.json"
PET = timezone(timedelta(hours=-5))  # hora de Perú

META_BASE = {
    "idEleccion": 10,
    "fuente": "resultadosegundavuelta.onpe.gob.pe",
    "candidatos": {
        "keiko":   {"nombre": "Keiko Fujimori",  "partido": "Fuerza Popular",     "color": "#1a2438"},
        "roberto": {"nombre": "Roberto Sánchez", "partido": "Juntos por el Perú", "color": "#9d3d3d"},
    },
    "benchmark_ipsos": {
        "etiqueta": "Conteo rápido Ipsos/Transparencia 100%",
        "keiko": 49.7, "roberto": 50.3, "margen": 1.9,
    },
}


def num(v):
    try:
        return float(v) if v is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def ahora_iso():
    return datetime.now(PET).isoformat(timespec="seconds")


def fila_region(ubigeo, nombre, totales, participantes):
    cand = extraer_candidatos(participantes)
    kv, rv = cand["keiko"]["votos"], cand["roberto"]["votos"]
    kp, rp = pct_sobre_dos(kv, rv)
    total_actas = int(num(totales.get("totalActas")))
    contab = int(num(totales.get("contabilizadas")))
    return {
        "ubigeo": ubigeo,
        "region": nombre,
        "actas_total": total_actas,
        "contabilizadas": contab,
        "pendientes": total_actas - contab,
        "actas_pct": round(num(totales.get("actasContabilizadas")), 3),
        "votos_emitidos": int(num(totales.get("totalVotosEmitidos"))),
        "votos_validos": int(num(totales.get("totalVotosValidos"))),
        "participacion_pct": round(num(totales.get("participacionCiudadana")), 3),
        "keiko_votos": int(kv),
        "roberto_votos": int(rv),
        "keiko_pct": kp,
        "roberto_pct": rp,
        "lider": ("keiko" if kv > rv else "roberto" if rv > kv else "empate"),
    }


def agregar(acum, r):
    for k in ("actas_total", "contabilizadas", "pendientes", "votos_emitidos",
              "votos_validos", "keiko_votos", "roberto_votos"):
        acum[k] = acum.get(k, 0) + r[k]


def main():
    dry = "--dry-run" in sys.argv
    cli = OnpeClient()

    deps = cli.departamentos()
    if not deps:
        print("[scrape-2v] ERROR: no se pudo obtener la lista de departamentos (WAF/red).")
        sys.exit(1)

    regiones = []
    nacional = {}
    print(f"[scrape-2v] consultando {len(deps)} departamentos…")
    for d in deps:
        ub, nom = d.get("ubigeo"), d.get("nombre")
        tot = cli.totales_departamento(ub)
        par = cli.participantes_departamento(ub)
        if not tot or par is None:
            print(f"  ! {nom}: sin datos, se omite")
            continue
        r = fila_region(ub, nom, tot, par)
        regiones.append(r)
        agregar(nacional, r)
        print(f"  · {nom:<16} {r['actas_pct']:5.1f}%  K {r['keiko_pct'] or 0:5.2f} / R {r['roberto_pct'] or 0:5.2f}  pend {r['pendientes']}")

    # Extranjero (estrato aparte)
    et = cli.totales_extranjero()
    ep = cli.participantes_extranjero()
    extranjero = None
    if et:
        extranjero = fila_region("EXTRANJERO", "EXTRANJERO", et, ep or [])
        print(f"  · {'EXTRANJERO':<16} {extranjero['actas_pct']:5.1f}%  K {extranjero['keiko_pct'] or 0:5.2f} / R {extranjero['roberto_pct'] or 0:5.2f}  pend {extranjero['pendientes']}")

    # Nacional = suma de regiones (+ extranjero) — y su % derivado
    nac = dict(nacional)
    if extranjero:
        agregar(nac, extranjero)
    kp, rp = pct_sobre_dos(nac.get("keiko_votos", 0), nac.get("roberto_votos", 0))
    nac["actas_pct"] = round(100 * nac.get("contabilizadas", 0) / nac["actas_total"], 3) if nac.get("actas_total") else 0
    nac["keiko_pct"], nac["roberto_pct"] = kp, rp

    corte = {"ts": ahora_iso(), "nacional": nac, "regiones": regiones, "extranjero": extranjero}

    print(f"\n[scrape-2v] NACIONAL: {nac['actas_pct']:.2f}% actas | "
          f"Keiko {kp:.2f}% / Roberto {rp:.2f}% | pendientes {nac.get('pendientes', 0)}")

    if dry:
        print("[scrape-2v] --dry-run: no se escribe.")
        return

    # Cargar serie existente o inicializar
    if DATA_PATH.exists():
        db = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    else:
        DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
        db = {"meta": dict(META_BASE), "cortes": []}
    db.setdefault("cortes", [])
    db.setdefault("meta", dict(META_BASE))

    # Antiduplicado: si no avanzó el % nacional ni cambiaron los votos, no agregar.
    if db["cortes"]:
        ult = db["cortes"][-1]["nacional"]
        if (round(ult.get("actas_pct", -1), 3) == round(nac["actas_pct"], 3)
                and ult.get("keiko_votos") == nac.get("keiko_votos")):
            print("[scrape-2v] sin cambios respecto al último corte; no se agrega punto.")
            return

    db["cortes"].append(corte)
    db["meta"]["actualizado"] = corte["ts"]
    DATA_PATH.write_text(json.dumps(db, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[scrape-2v] serie actualizada: {len(db['cortes'])} cortes → {DATA_PATH}")


if __name__ == "__main__":
    main()
