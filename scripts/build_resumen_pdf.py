#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Resumen ejecutivo de 2 páginas enfocado en la PREDICCIÓN — Segunda Vuelta 2026.
Lee docs/data/proyeccion.json (+ serie-2v.json para el mapa) y genera
resumen-prediccion.pdf.

  Página 1 — La predicción: números, banda, veredicto, contraste y escenarios.
  Página 2 — El sustento: mapa de predominancia, actas que faltan y metodología.

Uso: python scripts/build_resumen_pdf.py [--out ruta.pdf]
"""
import sys
import json
import argparse
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, white
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle, HRFlowable, PageBreak, Image)
from reportlab.graphics.shapes import Drawing, Rect, Line

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_informe_pdf import generar_mapa_png  # noqa: E402

DATA = Path(__file__).resolve().parent.parent / "docs" / "data"
KEIKO = HexColor("#1a2438"); ROBERTO = HexColor("#9d3d3d"); INK = HexColor("#1a2438")
MUTE = HexColor("#6f675b"); RULE = HexColor("#c9bfb0"); BG = HexColor("#f1ebdf")
WARN = HexColor("#8a5a1a"); BGW = HexColor("#fbf4e6")
W = 174 * mm  # ancho útil


def barra(k, w=W, h=15, marca50=False):
    """Barra horizontal Keiko/Roberto proporcional, con marca opcional del 50%."""
    d = Drawing(w, h)
    kw = w * k / 100.0
    d.add(Rect(0, 0, kw, h, fillColor=KEIKO, strokeColor=None))
    d.add(Rect(kw, 0, w - kw, h, fillColor=ROBERTO, strokeColor=None))
    if marca50:
        d.add(Line(w / 2, -3, w / 2, h + 3, strokeColor=HexColor("#1c1a17"), strokeWidth=1.2))
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    args = ap.parse_args()
    proy = json.loads((DATA / "proyeccion.json").read_text(encoding="utf-8"))
    serie = json.loads((DATA / "serie-2v.json").read_text(encoding="utf-8"))
    out = args.out or str(Path(__file__).resolve().parent.parent / "resumen-prediccion.pdf")

    pr = proy["proyeccion"]
    k, r = pr["keiko_pct"], pr["roberto_pct"]
    lo, hi = pr["banda95_keiko"]
    ip = proy["validacion"]["ipsos"]
    cr = proy["crudo"]
    z = proy["pendientes_por_zona"]
    actas = proy["meta"]["actas_pct_nacional"]
    abierto = not pr["ganador_definido"]

    S = getSampleStyleSheet()
    S.add(ParagraphStyle("Tit", fontName="Times-Bold", fontSize=22, leading=25, textColor=INK))
    S.add(ParagraphStyle("Sub", fontName="Times-Italic", fontSize=11, leading=14, textColor=MUTE))
    S.add(ParagraphStyle("H2", fontName="Times-Bold", fontSize=14, leading=17, textColor=INK, spaceBefore=10, spaceAfter=4))
    S.add(ParagraphStyle("Big", fontName="Times-Bold", fontSize=46, leading=46, alignment=TA_CENTER))
    S.add(ParagraphStyle("CenterB", fontName="Helvetica-Bold", fontSize=11, alignment=TA_CENTER, textColor=INK))
    S.add(ParagraphStyle("Bn", fontName="Helvetica", fontSize=8.5, leading=11, alignment=TA_CENTER, textColor=MUTE))
    S.add(ParagraphStyle("Verd", fontName="Helvetica-Bold", fontSize=12.5, leading=16, alignment=TA_CENTER, textColor=WARN))
    S.add(ParagraphStyle("P", fontName="Times-Roman", fontSize=10, leading=14, alignment=TA_JUSTIFY, textColor=INK))
    S.add(ParagraphStyle("CellH", fontName="Helvetica-Bold", fontSize=8.5, textColor=white))
    S.add(ParagraphStyle("Cell", fontName="Helvetica", fontSize=9, textColor=INK))
    S.add(ParagraphStyle("CellR", parent=S["Cell"], alignment=2))
    S.add(ParagraphStyle("Lbl", fontName="Helvetica", fontSize=9, textColor=MUTE))
    S.add(ParagraphStyle("Foot", fontName="Helvetica", fontSize=7.5, leading=10, textColor=MUTE))

    def hr():
        return [Spacer(1, 4), HRFlowable(width="100%", color=RULE, thickness=.7), Spacer(1, 6)]

    story = []

    # ───────────────────────── PÁGINA 1 — LA PREDICCIÓN ─────────────────────────
    story.append(Paragraph("Segunda Vuelta 2026 — ¿Quién gana?", S["Tit"]))
    story.append(Paragraph(f"Proyección al 100% sobre datos oficiales ONPE · {actas:.1f}% de actas contabilizadas · "
                           f"{proy['meta']['ts'][:16].replace('T', ' ')}", S["Sub"]))
    story += hr()

    big = Table([[Paragraph(f'<font color="#1a2438">{k:.1f}%</font>', S["Big"]),
                  Paragraph(f'<font color="#9d3d3d">{r:.1f}%</font>', S["Big"])],
                 [Paragraph("KEIKO FUJIMORI", S["CenterB"]), Paragraph("ROBERTO SÁNCHEZ", S["CenterB"])],
                 [Paragraph("Fuerza Popular", S["Bn"]), Paragraph("Juntos por el Perú", S["Bn"])],
                 [Paragraph(f"rango probable {lo:.1f}–{hi:.1f}%", S["Bn"]),
                  Paragraph(f"rango probable {100-hi:.1f}–{100-lo:.1f}%", S["Bn"])]],
                colWidths=[W / 2, W / 2])
    big.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("BOTTOMPADDING", (0, 0), (-1, 0), 0)]))
    story.append(big)
    story.append(Spacer(1, 10))
    story.append(barra(k, marca50=True))
    story.append(Paragraph("▲ la línea marca el 50%: el resultado está prácticamente sobre ella", S["Bn"]))
    story.append(Spacer(1, 12))

    if abierto:
        verd = "RESULTADO ABIERTO — empate técnico, todavía no puede declararse un ganador"
    else:
        lider = "KEIKO FUJIMORI" if pr["lider"] == "keiko" else "ROBERTO SÁNCHEZ"
        verd = f"LEVE VENTAJA DE {lider} — pero dentro del margen de error; tratar como resultado abierto"
    vt = Table([[Paragraph(verd, S["Verd"])]], colWidths=[W])
    vt.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), BGW), ("BOX", (0, 0), (-1, -1), .9, HexColor("#e4cfa0")),
                            ("TOPPADDING", (0, 0), (-1, -1), 9), ("BOTTOMPADDING", (0, 0), (-1, -1), 9)]))
    story.append(vt)

    # Contraste de fuentes (3 barras)
    story.append(Paragraph("Las tres miradas del resultado", S["H2"]))
    fuentes = [("Conteo crudo ONPE (parcial, sesgado a Lima)", cr["keiko_pct"]),
               ("Proyección por región (esta estimación)", k),
               ("Conteo rápido Ipsos / Transparencia (100%)", ip["keiko"])]
    frows = []
    for lbl, kk in fuentes:
        frows.append([Paragraph(lbl, S["Lbl"]), barra(kk, w=78 * mm, h=11),
                      Paragraph(f"<b>{kk:.1f}</b> / {100-kk:.1f}", S["CellR"])])
    ft = Table(frows, colWidths=[68 * mm, 80 * mm, 26 * mm])
    ft.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                            ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    story.append(ft)
    story.append(Paragraph("Keiko / Roberto (%). Las tres se solapan en torno al 50%: por eso es un final abierto.", S["Bn"]))

    # Escenarios
    story.append(Paragraph("¿Y si las actas que faltan votan distinto?", S["H2"]))
    head = [Paragraph(f"<b>{h}</b>", S["CellH"]) for h in ("Si las mesas que faltan…", "Keiko", "Roberto", "Resultado")]
    et = {0: "Terminan igual que su región", 2: "Se inclinan un poco más a Sánchez",
          4: "Se inclinan bastante más a Sánchez", 6: "Se inclinan mucho más a Sánchez"}
    rows = [head]
    for e in proy["escenarios"]:
        rows.append([Paragraph(et.get(e["delta_pp"], f"−{e['delta_pp']} pp"), S["Cell"]),
                     Paragraph(f"{e['keiko_pct']:.1f}%", S["CellR"]),
                     Paragraph(f"{e['roberto_pct']:.1f}%", S["CellR"]),
                     Paragraph(e["resultado"], S["Cell"])])
    t = Table(rows, colWidths=[70 * mm, 26 * mm, 26 * mm, 52 * mm])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), KEIKO), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, BG]),
                           ("GRID", (0, 0), (-1, -1), .4, RULE), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                           ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    story.append(t)

    story.append(PageBreak())

    # ───────────────────────── PÁGINA 2 — EL SUSTENTO ─────────────────────────
    story.append(Paragraph("¿Por qué? El mapa y las actas que faltan", S["Tit"]))
    story.append(Paragraph("De dónde sale la proyección: el resultado por región y dónde está el voto sin contar.", S["Sub"]))
    story += hr()

    mapbuf = generar_mapa_png(serie)
    pend_rows = sorted([x for x in proy["regiones"] if x.get("keiko_pct_actual") is not None],
                       key=lambda x: -x["pendientes"])[:12]
    prows = [[Paragraph("<b>Región</b>", S["CellH"]), Paragraph("<b>Pend.</b>", S["CellH"]),
              Paragraph("<b>Keiko</b>", S["CellH"]), Paragraph("<b>Roberto</b>", S["CellH"])]]
    for x in pend_rows:
        prows.append([Paragraph(x["region"].title(), S["Cell"]),
                      Paragraph(f"{x['pendientes']:,}".replace(",", " "), S["CellR"]),
                      Paragraph(f"{x['keiko_pct_actual']:.0f}%", S["CellR"]),
                      Paragraph(f"{x['roberto_pct_actual']:.0f}%", S["CellR"])])
    ptab = Table(prows, colWidths=[34 * mm, 18 * mm, 16 * mm, 18 * mm], repeatRows=1)
    ptab.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), KEIKO), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, BG]),
                              ("GRID", (0, 0), (-1, -1), .4, RULE), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                              ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5)]))

    derecha = [Paragraph("Predominancia hoy", S["H2"]),
               Paragraph("Azul: lidera Keiko · Granate: lidera Sánchez · intensidad = margen.", S["Bn"]),
               Spacer(1, 6),
               Paragraph(f"<b>Faltan {z['total']:,} actas</b>".replace(",", " "), S["Cell"]),
               Paragraph(f"· {z['keiko_actas']:,} en zonas de Keiko".replace(",", " "), S["Lbl"]),
               Paragraph(f"· {z['roberto_actas']:,} en zonas de Sánchez".replace(",", " "), S["Lbl"]),
               Paragraph(f"· {z['extranjero_actas']:,} del extranjero (sin escrutar)".replace(",", " "), S["Lbl"]),
               Spacer(1, 8),
               Paragraph("Regiones con más actas por contar:", S["Cell"]),
               Spacer(1, 3), ptab]

    if mapbuf:
        img = Image(mapbuf, width=82 * mm, height=117 * mm)
        layout = Table([[img, derecha]], colWidths=[88 * mm, 86 * mm])
        layout.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (1, 0), (1, 0), 8)]))
        story.append(layout)
    else:
        story += derecha

    story.append(Paragraph("Cómo se hizo esta proyección", S["H2"]))
    story.append(Paragraph(
        "El conteo crudo de la ONPE favorece a Keiko porque Lima y el Callao —donde es fuerte— envían sus actas "
        "primero. Para corregirlo, se proyecta <b>región por región</b>: a cada una se le da el peso de su propio "
        "padrón (no de cuántas actas ya envió) y se estima su voto faltante con la tasa que esa misma región ya "
        "viene mostrando. El <b>rango probable</b> combina el azar del muestreo con la incertidumbre de los "
        "escenarios (si las zonas rurales, que cuentan más lento, votan algo más a Sánchez). Se valida contra el "
        "conteo rápido de Ipsos/Transparencia.", S["P"]))

    story += hr()
    story.append(Paragraph(
        "Proyección propia (método estratificado por región) sobre datos oficiales de la ONPE; el conteo rápido de "
        "Ipsos/Transparencia es referencia de observador acreditado. Este resumen NO afirma irregularidades ni "
        "fraude: es una estimación estadística. El resultado oficial y definitivo lo proclama el Jurado Nacional de "
        "Elecciones (JNE) a mediados de julio. Datos preliminares, sujetos a cambio.", S["Foot"]))

    SimpleDocTemplate(out, pagesize=A4, topMargin=16 * mm, bottomMargin=14 * mm,
                      leftMargin=18 * mm, rightMargin=18 * mm, title="Resumen predicción 2V 2026").build(story)
    print(f"[resumen] one-pager (2 págs) generado: {out}")


if __name__ == "__main__":
    main()
