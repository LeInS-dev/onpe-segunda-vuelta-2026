#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Motor de PROYECCIÓN al 100% — Segunda Vuelta 2026.

Estimador estratificado por región: en lugar de extrapolar el % nacional crudo
(sesgado porque Lima/Callao entran primero y votan más a Keiko), proyecta cada
región por separado y suma. Las actas que faltan en cada región se estiman con:
  · lo que ya votó esa misma región (p_s), y
  · su preferencia de 1ª vuelta corregida por el "swing" nacional (prior).
El peso de cada región es su propio volumen de votos (actas pendientes × votos/acta),
así que Lima no infla el total solo por contar primero.

Entradas:  docs/data/serie-2v.json (último corte), docs/data/participacion_1v_2026.json
Salida:    docs/data/proyeccion.json

Reporta: proyección puntual + banda 95% (Monte Carlo) + escenarios de sensibilidad
(sesgo rural) + validación contra el conteo rápido de Ipsos. NO declara ganador si
la banda cruza el 50%.
"""
import sys
import json
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
from regiones import canon_region  # noqa: E402

DATA = Path(__file__).resolve().parent.parent / "docs" / "data"
SERIE = DATA / "serie-2v.json"
OUT = DATA / "proyeccion.json"

IPSOS = {"keiko": 49.7, "roberto": 50.3, "margen": 1.9}
N_SIM = 4000  # simulaciones Monte Carlo para la banda


def lcg(seed):
    """Generador congruencial simple (Math.random/Date no disponibles en workflows;
    semilla fija → reproducible). Devuelve floats en [0,1)."""
    x = seed & 0x7FFFFFFF
    while True:
        x = (1103515245 * x + 12345) & 0x7FFFFFFF
        yield x / 0x7FFFFFFF


def gauss(rng):
    """Box-Muller a partir de dos uniformes."""
    import math
    u1 = max(next(rng), 1e-12)
    u2 = next(rng)
    return math.sqrt(-2 * math.log(u1)) * math.cos(2 * math.pi * u2)


def main():
    serie = json.loads(SERIE.read_text(encoding="utf-8"))
    corte = serie["cortes"][-1]
    regiones = list(corte["regiones"])
    if corte.get("extranjero"):
        regiones = regiones + [corte["extranjero"]]

    # --- proyección puntual por región ---
    # Cada región proyecta sus actas faltantes con su PROPIA tasa actual (q_s = p_s).
    # No se usa prior de 1ª vuelta: la fuente regional de 1V (BD local) tiene los
    # códigos de departamento desordenados y no es confiable a nivel regional.
    det = []
    K_fin = R_fin = 0.0
    K_now = R_now = 0.0
    for r in regiones:
        key = canon_region(r["region"])
        kv, rv = r["keiko_votos"], r["roberto_votos"]
        contab = r["contabilizadas"] or 0
        pend = r.get("pendientes", 0)
        val = r["votos_validos"] or (kv + rv)
        contados = kv + rv
        K_now += kv
        R_now += rv

        # votos válidos que faltan en la región ≈ (válidos por acta) × actas pendientes
        vpa = (val / contab) if contab else 0.0
        v_falt = vpa * pend

        a_s = min(max(r["actas_pct"] / 100.0, 0.0), 1.0)
        p_s = (kv / contados) if contados else None

        # Actas faltantes votan como lo ya contado de su región (extranjero: 50% neutral).
        q_s = 0.50 if p_s is None else p_s

        K_fin += kv + v_falt * q_s
        R_fin += rv + v_falt * (1 - q_s)
        det.append({
            "region": r["region"], "key": key, "actas_pct": r["actas_pct"],
            "keiko_pct_actual": r.get("keiko_pct"), "roberto_pct_actual": r.get("roberto_pct"),
            "pendientes": pend, "votos_falt_est": int(v_falt),
            "q_keiko_falt": round(100 * q_s, 2),
            "lider": r.get("lider"),
            "_v_falt": v_falt, "_a": a_s, "_p": p_s, "_q": q_s, "_kv": kv, "_rv": rv,
        })

    proy_keiko = 100 * K_fin / (K_fin + R_fin)
    crudo_keiko = 100 * K_now / (K_now + R_now)

    # --- banda 95% por Monte Carlo (incertidumbre del comportamiento faltante) ---
    rng = lcg(20260608)
    sims = []
    for _ in range(N_SIM):
        Ks = Rs = 0.0
        for d in det:
            if d["_p"] is None and d["key"] != "EXTRANJERO":
                continue
            # σ mayor cuanto menos avance tiene la región (más incertidumbre)
            sigma = 0.05 * (1 - d["_a"]) + 0.015
            if d["key"] == "EXTRANJERO":
                sigma = 0.12  # extranjero: muy incierto
            q = min(max(d["_q"] + sigma * gauss(rng), 0.0), 1.0)
            Ks += d["_kv"] + d["_v_falt"] * q
            Rs += d["_rv"] + d["_v_falt"] * (1 - q)
        sims.append(100 * Ks / (Ks + Rs))
    sims.sort()
    mc_lo = sims[int(0.025 * len(sims))]
    mc_hi = sims[int(0.975 * len(sims))]

    # --- escenarios de sensibilidad (sesgo rural: las faltantes votan Δ pp menos a Keiko) ---
    escenarios = []
    for delta in (0, 2, 4, 6):
        Ks = Rs = 0.0
        for d in det:
            if d["_p"] is None and d["key"] != "EXTRANJERO":
                continue
            q = min(max(d["_q"] - delta / 100.0, 0.0), 1.0)
            Ks += d["_kv"] + d["_v_falt"] * q
            Rs += d["_rv"] + d["_v_falt"] * (1 - q)
        pk = 100 * Ks / (Ks + Rs)
        escenarios.append({
            "delta_pp": delta, "keiko_pct": round(pk, 2), "roberto_pct": round(100 - pk, 2),
            "resultado": ("empate/Sánchez" if pk < 50 else "Keiko muy ajustado" if pk < 50.7
                          else "Keiko por poco" if pk < 51.3 else "Keiko"),
        })

    # --- pendientes por zona (responde a la pregunta del jefe) ---
    # El extranjero tiene su propio cubo (pend_ext); se excluye de las zonas
    # domésticas para que los tres sumen el total real y no se cuente doble.
    pend_k = sum(r["pendientes"] for r in regiones
                 if r.get("lider") == "keiko" and r.get("ubigeo") != "EXTRANJERO")
    pend_r = sum(r["pendientes"] for r in regiones
                 if r.get("lider") == "roberto" and r.get("ubigeo") != "EXTRANJERO")
    pend_ext = (corte["extranjero"]["pendientes"] if corte.get("extranjero") else 0)

    # Banda HONESTA = incertidumbre estadística (Monte Carlo) + incertidumbre de
    # MODELO (escenarios de sesgo rural 0–4 pp). La banda MC sola subestima el riesgo.
    esc_keikos = [e["keiko_pct"] for e in escenarios if e["delta_pp"] <= 4]
    lo = min(mc_lo, min(esc_keikos))
    hi = max(mc_hi, max(esc_keikos))
    ganador_definido = lo > 50 or hi < 50
    dentro_ipsos = (lo <= IPSOS["keiko"] + IPSOS["margen"]) and (hi >= IPSOS["keiko"] - IPSOS["margen"])

    out = {
        "meta": {
            "ts": corte["ts"],
            "actas_pct_nacional": corte["nacional"]["actas_pct"],
            "metodo": ("Estimador estratificado por región: cada región proyecta sus actas faltantes "
                       "con su tasa actual, ponderada por su volumen; banda 95% Monte Carlo + escenarios."),
        },
        "crudo": {
            "keiko_pct": round(crudo_keiko, 2), "roberto_pct": round(100 - crudo_keiko, 2),
        },
        "proyeccion": {
            "keiko_pct": round(proy_keiko, 2), "roberto_pct": round(100 - proy_keiko, 2),
            "banda95_keiko": [round(lo, 2), round(hi, 2)],
            "banda95_roberto": [round(100 - hi, 2), round(100 - lo, 2)],
            "banda_montecarlo_keiko": [round(mc_lo, 2), round(mc_hi, 2)],
            "ganador_definido": ganador_definido,
            "lider": "keiko" if proy_keiko > 50 else "roberto",
        },
        "escenarios": escenarios,
        "validacion": {
            "ipsos": IPSOS,
            "balarezo_estratificado_keiko": 51.4,
            "proyeccion_dentro_rango_ipsos": dentro_ipsos,
        },
        "pendientes_por_zona": {
            "keiko_actas": pend_k, "roberto_actas": pend_r, "extranjero_actas": pend_ext,
            "total": pend_k + pend_r + pend_ext,
        },
        "regiones": [{k: v for k, v in d.items() if not k.startswith("_")} for d in det],
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # --- resumen por consola ---
    print(f"[proy] corte {corte['nacional']['actas_pct']:.1f}% actas | método: cada región mantiene su tasa")
    print(f"[proy] CRUDO:      Keiko {out['crudo']['keiko_pct']:.2f}% / Roberto {out['crudo']['roberto_pct']:.2f}%")
    print(f"[proy] PROYECCIÓN: Keiko {out['proyeccion']['keiko_pct']:.2f}% [{lo:.2f}–{hi:.2f}] / "
          f"Roberto {out['proyeccion']['roberto_pct']:.2f}%")
    print(f"[proy] ganador definido (banda no cruza 50%): {ganador_definido} | dentro rango Ipsos: {dentro_ipsos}")
    print("[proy] escenarios:")
    for e in escenarios:
        print(f"    Δ{e['delta_pp']}pp -> Keiko {e['keiko_pct']:.2f}% / Roberto {e['roberto_pct']:.2f}%  ({e['resultado']})")
    print(f"[proy] pendientes: zona Keiko {pend_k:,} | zona Roberto {pend_r:,} | extranjero {pend_ext:,}")
    print(f"[proy] -> {OUT.name}")


if __name__ == "__main__":
    main()
