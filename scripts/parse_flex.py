#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utilidades de parsing flexible para las respuestas de la API de la ONPE.

Portado/adaptado de la lógica de docs/scripts/scrape-onpe.mjs (Fase 1):
identificar a cada candidato por nombre/agrupación sin depender de índices fijos,
y normalizar texto (sin tildes, mayúsculas) para comparaciones robustas.
"""
import unicodedata

# Palabras clave para identificar a cada candidato en la respuesta de la ONPE.
# Se comparan (normalizadas) contra nombreAgrupacionPolitica + nombreCandidato.
MATCHERS = {
    "keiko":   ["FUERZA POPULAR", "KEIKO", "FUJIMORI"],
    "roberto": ["JUNTOS POR EL PERU", "ROBERTO", "SANCHEZ", "PALOMINO"],
}

# Códigos de agrupación confirmados en la API de 2ª vuelta 2026.
COD_KEIKO = 8     # FUERZA POPULAR
COD_ROBERTO = 10  # JUNTOS POR EL PERÚ


def norm(s):
    """Normaliza: quita tildes, pasa a mayúsculas, recorta espacios."""
    s = "" if s is None else str(s)
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.upper().strip()


def match_candidato(fila):
    """
    Dada una fila de 'participantes' (dict con nombreAgrupacionPolitica,
    nombreCandidato, codigoAgrupacionPolitica), devuelve 'keiko', 'roberto' o None.
    Prioriza el código de agrupación (más fiable) y cae a las keywords.
    """
    cod = fila.get("codigoAgrupacionPolitica")
    if cod == COD_KEIKO:
        return "keiko"
    if cod == COD_ROBERTO:
        return "roberto"
    hay = norm(fila.get("nombreAgrupacionPolitica", "")) + " " + norm(fila.get("nombreCandidato", ""))
    for clave, kws in MATCHERS.items():
        if any(norm(k) in hay for k in kws):
            return clave
    return None


def extraer_candidatos(participantes_data):
    """
    De la lista `data` del endpoint /participantes, extrae votos y % de cada
    candidato. Devuelve dict {keiko:{votos,pct}, roberto:{votos,pct}}.
    """
    out = {"keiko": {"votos": 0, "pct": 0.0}, "roberto": {"votos": 0, "pct": 0.0}}
    for fila in participantes_data or []:
        quien = match_candidato(fila)
        if quien:
            out[quien]["votos"] = _num(fila.get("totalVotosValidos"))
            out[quien]["pct"] = _num(fila.get("porcentajeVotosValidos"))
    return out


def _num(v):
    try:
        return float(v) if v is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def pct_sobre_dos(keiko_votos, roberto_votos):
    """% de cada candidato sobre la base de los dos finalistas (sin blancos/nulos)."""
    base = keiko_votos + roberto_votos
    if base <= 0:
        return None, None
    return round(100 * keiko_votos / base, 3), round(100 * roberto_votos / base, 3)
