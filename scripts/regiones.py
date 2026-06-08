#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mapeo y normalización de departamentos del Perú, para cruzar las tres fuentes:
  · 2V 2026  → nombre que da la API de la ONPE
  · 1V 2026  → substr(ubigeo,1,2) en la BD local (código INEI)
  · 2V 2021  → columna DEPARTAMENTO / UBIGEO del CSV de la PCM

La clave de cruce es el NOMBRE NORMALIZADO (sin tildes, mayúsculas, sin "PROVINCIAS").
"""
import unicodedata

# Código de departamento de 2 dígitos según ONPE (verificado en vivo contra la API
# de 2026 y contra la BD de 1ª vuelta). OJO: NO es el código INEI estándar —
# es alfabético con Callao desplazado al final: 07=CUSCO, 14=LIMA, 24=CALLAO.
ONPE_COD = {
    "01": "AMAZONAS", "02": "ANCASH", "03": "APURIMAC", "04": "AREQUIPA",
    "05": "AYACUCHO", "06": "CAJAMARCA", "07": "CUSCO", "08": "HUANCAVELICA",
    "09": "HUANUCO", "10": "ICA", "11": "JUNIN", "12": "LA LIBERTAD",
    "13": "LAMBAYEQUE", "14": "LIMA", "15": "LORETO", "16": "MADRE DE DIOS",
    "17": "MOQUEGUA", "18": "PASCO", "19": "PIURA", "20": "PUNO",
    "21": "SAN MARTIN", "22": "TACNA", "23": "TUMBES", "24": "CALLAO",
    "25": "UCAYALI",
}


def norm(s):
    """Mayúsculas, sin tildes, espacios colapsados."""
    s = "" if s is None else str(s)
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return " ".join(s.upper().split())


def canon_region(nombre):
    """
    Normaliza el nombre de un departamento a su clave canónica.
    Une 'LIMA PROVINCIAS' y 'LIMA METROPOLITANA' bajo 'LIMA'; marca extranjero.
    """
    n = norm(nombre)
    if not n:
        return None
    if "EXTRANJERO" in n or n in ("AFRICA", "AMERICA", "ASIA", "EUROPA", "OCEANIA"):
        return "EXTRANJERO"
    if n.startswith("LIMA"):
        return "LIMA"
    # variantes ortográficas frecuentes
    n = n.replace("ANCASH", "ANCASH").replace("APURIMAC", "APURIMAC")
    return n
