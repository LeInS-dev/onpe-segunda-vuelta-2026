#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
One-pager (1 hoja A4) enfocado en la PREDICCIÓN — Segunda Vuelta 2026.
Lee docs/data/proyeccion.json y genera resumen-prediccion.pdf.

Pensado para una lectura rápida de decisión: el número, la banda, el veredicto,
los escenarios y la comparación con el conteo rápido, sin tablas largas.
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
                                TableStyle, HRFlowable)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

DATA = Path(__file__).resolve().parent.parent / "docs" / "data"
KEIKO = HexColor("#1a2438"); ROBERTO = HexColor("#9d3d3d"); INK = HexColor("#1a2438")
MUTE = HexColor("#6f675b"); RULE = HexColor("#c9bfb0"); BG = HexColor("#f1ebdf")
WARN = HexColor("#8a5a1a"); BGW = HexColor("#fbf4e6")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    args = ap.parse_args()
    proy = json.loads((DATA / "proyeccion.json").read_text(encoding="utf-8"))
    out = args.out or str(Path(__file__).resolve().parent.parent / "resumen-prediccion.pdf")

    pr = proy["proyeccion"]
    k, r = pr["keiko_pct"], pr["roberto_pct"]
    lo, hi = pr["banda95_keiko"]
    ip = proy["validacion"]["ipsos"]
    z = proy["pendientes_por_zona"]
    actas = proy["meta"]["actas_pct_nacional"]
    abierto = not pr["ganador_definido"]

    S = getSampleStyleSheet()
    S.add(ParagraphStyle("Tit", fontName="Times-Bold", fontSize=21, leading=24, textColor=INK))
    S.add(ParagraphStyle("Sub", fontName="Times-Italic", fontSize=11, leading=14, textColor=MUTE))
    S.add(ParagraphStyle("Big", fontName="Times-Bold", fontSize=46, leading=46, alignment=TA_CENTER))
    S.add(ParagraphStyle("Nm", fontName="Helvetica-Bold", fontSize=11, leading=13, alignment=TA_CENTER, textColor=white))
    S.add(ParagraphStyle("Bn", fontName="Helvetica", fontSize=8.5, leading=11, alignment=TA_CENTER, textColor=MUTE))
    S.add(ParagraphStyle("Verd", fontName="Helvetica-Bold", fontSize=12.5, leading=16, alignment=TA_CENTER, textColor=WARN))
    S.add(ParagraphStyle("P", fontName="Times-Roman", fontSize=10, leading=14, alignment=TA_JUSTIFY, textColor=INK))
    S.add(ParagraphStyle("CellH", fontName="Helvetica-Bold", fontSize=8.5, textColor=white))
    S.add(ParagraphStyle("Cell", fontName="Helvetica", fontSize=9, textColor=INK))
    S.add(ParagraphStyle("CellR", parent=S["Cell"], alignment=2))
    S.add(ParagraphStyle("Foot", fontName="Helvetica", fontSize=7.5, leading=10, textColor=MUTE))

    story = []
    story.append(Paragraph("Segunda Vuelta 2026 — Proyección al 100%", S["Tit"]))
    story.append(Paragraph(f"Resumen ejecutivo · datos oficiales ONPE al {actas:.1f}% de actas · {proy['meta']['ts'][:16].replace('T',' ')}", S["Sub"]))
    story.append(Spacer(1, 4)); story.append(HRFlowable(width="100%", color=RULE, thickness=.8)); story.append(Spacer(1, 12))

    # Números grandes
    big = Table([[Paragraph(f'<font color="#1a2438">{k:.1f}%</font>', S["Big"]),
                  Paragraph(f'<font color="#9d3d3d">{r:.1f}%</font>', S["Big"])],
                 [Paragraph("KEIKO FUJIMORI", ParagraphStyle("x", parent=S["Cell"], alignment=TA_CENTER, fontName="Helvetica-Bold")),
                  Paragraph("ROBERTO SÁNCHEZ", ParagraphStyle("x", parent=S["Cell"], alignment=TA_CENTER, fontName="Helvetica-Bold"))],
                 [Paragraph("Fuerza Popular", S["Bn"]), Paragraph("Juntos por el Perú", S["Bn"])],
                 [Paragraph(f"banda 95%: {lo:.1f}–{hi:.1f}", S["Bn"]),
                  Paragraph(f"banda 95%: {100-hi:.1f}–{100-lo:.1f}", S["Bn"])]],
                colWidths=[85 * mm, 85 * mm])
    big.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("BOTTOMPADDING", (0, 0), (-1, 0), 2)]))
    story.append(big)
    story.append(Spacer(1, 10))

    # Barra proporcional con 50%
    bar = Table([[Paragraph(f"Keiko {k:.1f}%", S["Nm"]), Paragraph(f"Roberto {r:.1f}%", S["Nm"])]],
                colWidths=[170 * mm * k / 100, 170 * mm * r / 100], rowHeights=[16])
    bar.setStyle(TableStyle([("BACKGROUND", (0, 0), (0, 0), KEIKO), ("BACKGROUND", (1, 0), (1, 0), ROBERTO),
                             ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 6),
                             ("RIGHTPADDING", (0, 0), (-1, -1), 6)]))
    story.append(bar)
    story.append(Paragraph("▲ línea del 50% — el resultado está prácticamente sobre ella", S["Bn"]))
    story.append(Spacer(1, 12))

    # Veredicto
    if abierto:
        verd = "RESULTADO ABIERTO — empate técnico, no puede declararse ganador"
    else:
        lider = "Keiko Fujimori" if pr["lider"] == "keiko" else "Roberto Sánchez"
        verd = f"VENTAJA MÍNIMA DE {lider.upper()} — pero dentro del margen; tratar como resultado abierto"
    vt = Table([[Paragraph(verd, S["Verd"])]], colWidths=[170 * mm])
    vt.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), BGW), ("BOX", (0, 0), (-1, -1), .8, HexColor("#e4cfa0")),
                            ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    story.append(vt)
    story.append(Spacer(1, 12))

    # Escenarios (compacto)
    story.append(Paragraph("<b>Escenarios</b> — qué pasa según cómo voten las actas que faltan:", S["P"]))
    head = [Paragraph(f"<b>{h}</b>", S["CellH"]) for h in ("Si las mesas que faltan…", "Keiko", "Roberto", "Resultado")]
    rows = [head]
    et = {0: "votan igual que su región", 2: "le dan 2 pts menos a Keiko",
          4: "le dan 4 pts menos a Keiko", 6: "le dan 6 pts menos a Keiko"}
    for e in proy["escenarios"]:
        rows.append([Paragraph(et.get(e["delta_pp"], f"−{e['delta_pp']} pp"), S["Cell"]),
                     Paragraph(f"{e['keiko_pct']:.1f}%", S["CellR"]),
                     Paragraph(f"{e['roberto_pct']:.1f}%", S["CellR"]),
                     Paragraph(e["resultado"], S["Cell"])])
    t = Table(rows, colWidths=[68 * mm, 26 * mm, 26 * mm, 50 * mm])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), KEIKO), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, BG]),
                           ("GRID", (0, 0), (-1, -1), .4, RULE), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                           ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    story.append(Spacer(1, 4)); story.append(t)
    story.append(Spacer(1, 12))

    # Contexto clave
    story.append(Paragraph(
        f"<b>Contraste.</b> El conteo crudo de la ONPE da Keiko {proy['crudo']['keiko_pct']:.1f}%, pero está sesgado "
        f"porque Lima y Callao (pro-Keiko) entran primero; por eso proyectamos región por región. El <b>conteo rápido "
        f"de Ipsos/Transparencia</b> al 100% dio el resultado inverso: Keiko {ip['keiko']}% / Roberto {ip['roberto']}% "
        f"(±{ip['margen']}). Ambos se solapan en torno al 50%.", S["P"]))
    story.append(Paragraph(
        f"<b>Lo que falta.</b> Quedan {z['total']:,} actas por contar: {z['keiko_actas']:,} en regiones que hoy "
        f"lidera Keiko, {z['roberto_actas']:,} donde lidera Sánchez y {z['extranjero_actas']:,} del extranjero "
        f"(sin escrutar; en 2021 favoreció a Keiko).".replace(",", " "), S["P"]))

    story.append(Spacer(1, 10)); story.append(HRFlowable(width="100%", color=RULE, thickness=.6)); story.append(Spacer(1, 4))
    story.append(Paragraph(
        "Proyección propia por método estratificado por región sobre datos oficiales de la ONPE; el conteo rápido de "
        "Ipsos/Transparencia es referencia de observador acreditado. Este resumen NO afirma irregularidades ni fraude. "
        "El resultado oficial y definitivo lo proclama el Jurado Nacional de Elecciones (JNE) a mediados de julio. "
        "Datos preliminares sujetos a cambio.", S["Foot"]))

    SimpleDocTemplate(out, pagesize=A4, topMargin=16 * mm, bottomMargin=14 * mm,
                      leftMargin=20 * mm, rightMargin=20 * mm, title="Resumen predicción 2V 2026").build(story)
    print(f"[resumen] one-pager generado: {out}")


if __name__ == "__main__":
    main()
