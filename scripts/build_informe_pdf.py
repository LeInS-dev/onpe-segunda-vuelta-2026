#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Informe PDF exportable de la Segunda Vuelta 2026: proyección por región +
participación. Lee los JSON de docs/data/ y produce informe-2v-<ts>.pdf.

Diseño editorial A4 con ReportLab; paleta heredada del proyecto de Fase 1.
Uso: python scripts/build_informe_pdf.py [--out ruta.pdf]
"""
import sys
import io
import math
import json
import argparse
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, white
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle, HRFlowable, Image)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
from regiones import canon_region  # noqa: E402

DATA = Path(__file__).resolve().parent.parent / "docs" / "data"
GEOJSON = DATA.parent / "assets" / "peru-departamentos.geojson"

INK = HexColor("#1a2438"); ACCENT = HexColor("#9d3d3d"); CONFIRM = HexColor("#3d6b4a")
WARN = HexColor("#b88a2c"); RULE = HexColor("#c9bfb0"); MUTE = HexColor("#6f675b")
BG_CARD = HexColor("#f1ebdf"); BG_HEAD = HexColor("#1a2438")


def styles():
    s = getSampleStyleSheet()
    s.add(ParagraphStyle("T", fontName="Times-Bold", fontSize=26, leading=30, textColor=INK, spaceAfter=4))
    s.add(ParagraphStyle("Sub", fontName="Times-Italic", fontSize=12.5, leading=16, textColor=MUTE, spaceAfter=14))
    s.add(ParagraphStyle("H2", fontName="Times-Bold", fontSize=16, leading=20, textColor=INK, spaceBefore=16, spaceAfter=6))
    s.add(ParagraphStyle("H3", fontName="Times-Bold", fontSize=12, leading=15, textColor=ACCENT, spaceBefore=8, spaceAfter=3))
    s.add(ParagraphStyle("P", fontName="Times-Roman", fontSize=10.5, leading=15, textColor=INK, alignment=TA_JUSTIFY, spaceAfter=7))
    s.add(ParagraphStyle("Small", fontName="Helvetica", fontSize=8, leading=11, textColor=MUTE))
    s.add(ParagraphStyle("Cell", fontName="Helvetica", fontSize=8.5, leading=11, textColor=INK))
    s.add(ParagraphStyle("CellR", parent=s["Cell"], alignment=2))
    s.add(ParagraphStyle("CellH", fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=white))
    return s


def load(name):
    p = DATA / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def pct(x, d=2):
    return "—" if x is None else f"{x:.{d}f}%"


def miles(x):
    return "—" if x is None else f"{int(x):,}".replace(",", " ")


def generar_mapa_png(serie):
    """Mapa estático del Perú coloreado por líder (matplotlib) -> BytesIO PNG."""
    if not GEOJSON.exists():
        return None
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    geo = json.loads(GEOJSON.read_text(encoding="utf-8"))
    last = serie["cortes"][-1]
    by = {canon_region(r["region"]): r for r in last["regiones"]}

    fig, ax = plt.subplots(figsize=(4.6, 6.6))
    for f in geo["features"]:
        r = by.get(canon_region(f["properties"]["NOMBDEP"]))
        if r and r.get("keiko_pct") is not None and r["actas_pct"] > 0:
            base = "#1a2438" if r["lider"] == "keiko" else "#9d3d3d"
            al = 0.40 + min(abs(r["keiko_pct"] - 50) / 30, 1) * 0.60
        else:
            base, al = "#cdbfa8", 1.0
        g = f["geometry"]
        polys = g["coordinates"] if g["type"] == "Polygon" else [ring for poly in g["coordinates"] for ring in poly]
        for ring in polys:
            xs = [p[0] for p in ring]
            ys = [p[1] for p in ring]
            ax.fill(xs, ys, facecolor=base, alpha=al, edgecolor="white", linewidth=0.4)
    ax.set_aspect(1.0 / math.cos(math.radians(9.2)))
    ax.axis("off")
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", transparent=True)
    plt.close(fig)
    buf.seek(0)
    return buf


def cruzar_participacion(p1, p21, serie):
    """Devuelve filas por región: tasa 2V2021 / 1V2026 / 2V2026prov + votantes."""
    if not (p1 and p21):
        return []
    m1 = {canon_region(r["region"]): r for r in p1["regiones"]}
    m21 = {canon_region(r["region"]): r for r in p21["regiones"]}
    m2v = {}
    if serie and serie["cortes"]:
        for r in serie["cortes"][-1]["regiones"]:
            m2v[canon_region(r["region"])] = r.get("participacion_pct")
    out = []
    for key in [canon_region(r["region"]) for r in p1["regiones"]]:
        a, b = m1.get(key, {}), m21.get(key, {})
        out.append({
            "region": a.get("region", key),
            "p21": b.get("participacion_pct"), "p1v": a.get("participacion_pct"),
            "p2v": m2v.get(key), "v1v": a.get("votantes"), "v21": b.get("votantes"),
        })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    args = ap.parse_args()

    proy = load("proyeccion.json")
    serie = load("serie-2v.json")
    p1 = load("participacion_1v_2026.json")
    p21 = load("participacion_2v_2021.json")
    if not proy or not serie:
        print("Faltan proyeccion.json / serie-2v.json. Corré scrape_2v.py y proyeccion.py primero.")
        sys.exit(1)

    ts = proy["meta"]["ts"]
    out = args.out or str(Path(__file__).resolve().parent.parent / f"informe-2v-{ts[:13].replace(':','')}.pdf")
    S = styles()
    story = []

    def rule():
        story.append(Spacer(1, 4)); story.append(HRFlowable(width="100%", color=RULE, thickness=.7)); story.append(Spacer(1, 4))

    # ---------- Portada ----------
    story.append(Paragraph("Segunda Vuelta 2026 — Proyección por región", S["T"]))
    story.append(Paragraph(f"Informe técnico · corte ONPE al {proy['meta']['actas_pct_nacional']:.1f}% de actas · {ts}", S["Sub"]))
    rule()

    # ---------- Resumen ejecutivo ----------
    pr = proy["proyeccion"]; lo, hi = pr["banda95_keiko"]
    lider = "Keiko Fujimori" if pr["lider"] == "keiko" else "Roberto Sánchez"
    veredicto = ("una ventaja sostenible" if pr["ganador_definido"]
                 else "un <b>empate técnico</b> (la banda de incertidumbre cruza el 50%)")
    story.append(Paragraph("Resumen ejecutivo", S["H2"]))
    story.append(Paragraph(
        f"Con el {proy['meta']['actas_pct_nacional']:.1f}% de las actas contabilizadas, el conteo "
        f"crudo de la ONPE da <b>Keiko {pct(proy['crudo']['keiko_pct'])}</b> / "
        f"Roberto {pct(proy['crudo']['roberto_pct'])}. Pero ese número está sesgado porque las "
        f"primeras actas llegan de Lima y Callao, donde Keiko es fuerte. Nuestra <b>proyección "
        f"estratificada por región</b> al 100% estima <b>Keiko {pct(pr['keiko_pct'])}</b> "
        f"(banda 95%: {lo:.1f}–{hi:.1f}) frente a Roberto {pct(pr['roberto_pct'])}. "
        f"Esto configura {veredicto}, con leve ventaja de {lider}.", S["P"]))
    story.append(Paragraph(
        f"El conteo rápido de Ipsos/Transparencia al 100% dio un empate técnico "
        f"(Keiko {proy['validacion']['ipsos']['keiko']}% / Roberto {proy['validacion']['ipsos']['roberto']}%, "
        f"±{proy['validacion']['ipsos']['margen']}). Nuestra proyección "
        f"{'se solapa' if proy['validacion']['proyeccion_dentro_rango_ipsos'] else 'no se solapa'} con ese rango. "
        f"<b>El resultado oficial y definitivo lo proclama el JNE a mediados de julio.</b>", S["P"]))

    # tarjeta comparativa
    comp = [[Paragraph("<b>Fuente</b>", S["CellH"]), Paragraph("<b>Keiko</b>", S["CellH"]), Paragraph("<b>Roberto</b>", S["CellH"])],
            [Paragraph("Conteo crudo ONPE", S["Cell"]), Paragraph(pct(proy['crudo']['keiko_pct']), S["CellR"]), Paragraph(pct(proy['crudo']['roberto_pct']), S["CellR"])],
            [Paragraph("Proyección (propia)", S["Cell"]), Paragraph(pct(pr['keiko_pct']), S["CellR"]), Paragraph(pct(pr['roberto_pct']), S["CellR"])],
            [Paragraph("Conteo rápido Ipsos", S["Cell"]), Paragraph(f"{proy['validacion']['ipsos']['keiko']}%", S["CellR"]), Paragraph(f"{proy['validacion']['ipsos']['roberto']}%", S["CellR"])]]
    t = Table(comp, colWidths=[80*mm, 40*mm, 40*mm])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), BG_HEAD), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, BG_CARD]),
                           ("GRID", (0, 0), (-1, -1), .5, RULE), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                           ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    story.append(t); story.append(Spacer(1, 6))

    # escenarios
    story.append(Paragraph("Escenarios — si las actas faltantes votan menos a Keiko (sesgo rural):", S["H3"]))
    esc = [[Paragraph("<b>Supuesto</b>", S["CellH"]), Paragraph("<b>Keiko</b>", S["CellH"]), Paragraph("<b>Roberto</b>", S["CellH"]), Paragraph("<b>Resultado</b>", S["CellH"])]]
    for e in proy["escenarios"]:
        lbl = "mantienen su %" if e["delta_pp"] == 0 else f"−{e['delta_pp']} pp a Keiko"
        esc.append([Paragraph(lbl, S["Cell"]), Paragraph(f"{e['keiko_pct']:.2f}%", S["CellR"]),
                    Paragraph(f"{e['roberto_pct']:.2f}%", S["CellR"]), Paragraph(e["resultado"], S["Cell"])])
    t = Table(esc, colWidths=[55*mm, 30*mm, 30*mm, 45*mm])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), BG_HEAD), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, BG_CARD]),
                           ("GRID", (0, 0), (-1, -1), .5, RULE), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                           ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    story.append(t)

    # ---------- Metodología ----------
    story.append(Paragraph("Cómo se hizo la proyección", S["H2"]))
    story.append(Paragraph(
        "En lugar de extrapolar el porcentaje nacional crudo, se proyecta <b>región por región</b>. "
        "A cada región se le da el peso de su propio volumen de votos (no de cuántas actas ya entraron), "
        "de modo que Lima no infla el total solo por contar primero. Las actas que faltan en cada región "
        "se estiman con la <b>tasa que esa misma región ya viene mostrando</b> en lo escrutado. Luego se "
        "suman todas las regiones.", S["P"]))
    story.append(Paragraph(
        "La <b>banda 95%</b> combina la incertidumbre estadística (simulación Monte Carlo de las actas "
        "faltantes) con la incertidumbre del modelo (los escenarios de sesgo rural). Por eso es honesta: "
        "si cruza el 50%, no se declara ganador. <b>Supuestos clave:</b> las actas faltantes de una región "
        "se parecen a las ya contadas más el swing; el voto extranjero (que aún no se escruta) se trata "
        "aparte y con alta incertidumbre.", S["P"]))

    # ---------- Mapa de predominancia ----------
    mapbuf = generar_mapa_png(serie)
    if mapbuf:
        story.append(Paragraph("Mapa de predominancia por región", S["H2"]))
        story.append(Paragraph("Azul oscuro: lidera Keiko Fujimori · Granate: lidera Roberto Sánchez · "
                               "la intensidad indica el margen. Beige: sin escrutar (extranjero).", S["Small"]))
        story.append(Spacer(1, 4))
        img = Image(mapbuf, width=92 * mm, height=132 * mm)
        img.hAlign = "CENTER"
        story.append(img)

    # ---------- Pendientes por zona ----------
    z = proy["pendientes_por_zona"]
    story.append(Paragraph("¿Dónde están las actas que faltan?", S["H2"]))
    story.append(Paragraph(
        f"De las <b>{miles(z['total'])}</b> actas pendientes, <b>{miles(z['keiko_actas'])}</b> están en "
        f"regiones donde hoy lidera Keiko y <b>{miles(z['roberto_actas'])}</b> donde lidera Sánchez; "
        f"además quedan <b>{miles(z['extranjero_actas'])}</b> del extranjero sin escrutar (comodín que "
        f"históricamente favorece a Keiko).", S["P"]))

    # ---------- Tabla por región ----------
    story.append(Paragraph("Detalle por región", S["H2"]))
    head = [Paragraph(f"<b>{h}</b>", S["CellH"]) for h in ("Región", "% actas", "Keiko %", "Roberto %", "Pendientes", "Proy. Keiko %")]
    rows = [head]
    for r in sorted(proy["regiones"], key=lambda x: -(x["pendientes"] or 0)):
        rows.append([Paragraph(r["region"].title(), S["Cell"]),
                     Paragraph(f"{r['actas_pct']:.1f}%", S["CellR"]),
                     Paragraph(pct(r["keiko_pct_actual"], 1), S["CellR"]),
                     Paragraph(pct(r["roberto_pct_actual"], 1), S["CellR"]),
                     Paragraph(miles(r["pendientes"]), S["CellR"]),
                     Paragraph(pct(r["q_keiko_falt"], 1), S["CellR"])])
    t = Table(rows, colWidths=[42*mm, 22*mm, 24*mm, 26*mm, 26*mm, 28*mm], repeatRows=1)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), BG_HEAD), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, BG_CARD]),
                           ("GRID", (0, 0), (-1, -1), .4, RULE), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                           ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    story.append(t)

    # ---------- Participación ----------
    if p1 and p21:
        story.append(Paragraph("Participación: ¿votó más gente que antes?", S["H2"]))
        n1, n21 = p1["meta"]["nacional"], p21["meta"]["nacional"]
        h1 = n1.get("habiles") or n1.get("habiles_mapeado") or 0
        dpad = h1 - n21["habiles"]
        story.append(Paragraph(
            f"El padrón creció cerca de <b>{miles(dpad)} electores (~+{100*dpad/n21['habiles']:.1f}%)</b> entre 2021 y 2026. "
            f"La tasa de participación de la 2.ª vuelta 2021 fue {n21['participacion_pct']}% y la de la 1.ª vuelta "
            f"2026 fue {n1['participacion_pct']}%; la estimación final de la 2.ª vuelta 2026 (Transparencia) ronda el "
            f"72,4%. Conclusión honesta: <b>puede haber más votantes en número absoluto</b> (porque el padrón es "
            f"mayor), pero <b>la tasa no habría subido</b> respecto de 2021. No conviene afirmar que 'votó mucha "
            f"más gente que otros años' sin esa distinción.", S["P"]))

        # tabla de participación por región: 2V 2021 (final) vs 2V 2026 (provisional)
        filas = cruzar_participacion(p1, p21, serie)
        if filas:
            head = [Paragraph(f"<b>{h}</b>", S["CellH"]) for h in
                    ("Región", "2V 2021 (final)", "2V 2026 (prov.)", "Δ prov. (pp)", "Votantes 2021")]
            prows = [head]
            for r in sorted(filas, key=lambda x: -(x["p21"] or 0)):
                if r["p21"] is None:
                    continue
                delta = (r["p2v"] - r["p21"]) if (r["p2v"] is not None and r["p21"] is not None) else None
                prows.append([Paragraph(r["region"].title(), S["Cell"]),
                              Paragraph(pct(r["p21"], 1), S["CellR"]),
                              Paragraph((f"{r['p2v']:.1f}%" if r["p2v"] is not None else "—"), S["CellR"]),
                              Paragraph(("—" if delta is None else f"{delta:+.1f}"), S["CellR"]),
                              Paragraph(miles(r["v21"]), S["CellR"])])
            t = Table(prows, colWidths=[44 * mm, 30 * mm, 30 * mm, 26 * mm, 32 * mm], repeatRows=1)
            t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), BG_HEAD), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, BG_CARD]),
                                   ("GRID", (0, 0), (-1, -1), .4, RULE), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                                   ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
            story.append(Spacer(1, 4))
            story.append(t)
            story.append(Paragraph("La 2.ª vuelta 2026 es provisional (sube con el escrutinio); por eso el Δ es negativo "
                                   "ahora y se irá cerrando. Comparación 2.ª vuelta contra 2.ª vuelta.", S["Small"]))

    # ---------- Anexo ----------
    story.append(Paragraph("Limitaciones y nota editorial", S["H2"]))
    story.append(Paragraph(
        "Datos preliminares de la ONPE, sujetos a cambio. La proyección depende de supuestos sobre las actas "
        "no contadas; si el sur rural y el voto extranjero se desvían de lo esperado, el resultado puede "
        "moverse dentro de la banda. <b>Este informe no afirma irregularidades ni fraude</b>: presenta "
        "observaciones para que las verifique la ONPE. El resultado oficial lo proclama el JNE. "
        "Fuentes: ONPE (oficial) y conteo rápido de Ipsos/Transparencia (observador acreditado, referencia).", S["P"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph(f"Generado automáticamente · corte {ts} · método estratificado por región.", S["Small"]))

    doc = SimpleDocTemplate(out, pagesize=A4, topMargin=18*mm, bottomMargin=16*mm,
                            leftMargin=18*mm, rightMargin=18*mm, title="Informe 2V 2026")
    doc.build(story)
    print(f"[informe] PDF generado: {out}")


if __name__ == "__main__":
    main()
