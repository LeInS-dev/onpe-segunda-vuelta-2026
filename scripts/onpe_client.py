#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cliente de la API oficial de resultados de la ONPE — Segunda Vuelta 2026.

Dominio: https://resultadosegundavuelta.onpe.gob.pe
idEleccion=10  (segunda vuelta presidencial)

CLAVE (verificado en vivo 2026-06-08): el backend devuelve el HTML de la SPA
(o 403) ante peticiones que parecen "navegación". Para obtener JSON hay que
imitar una llamada XHR de Angular con los headers Sec-Fetch-* + X-Requested-With.
NO hace falta navegador headless (Playwright); requests basta.

El WAF aplica rate-limit ante ráfagas: se mete una pausa entre llamadas y
reintentos con backoff.
"""
import time
import requests

BASE = "https://resultadosegundavuelta.onpe.gob.pe"
ID_ELECCION = 10

# Headers que hacen que NGINX entregue JSON en vez del index.html de la SPA.
_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "es-PE,es;q=0.9",
    "Referer": BASE + "/",
    "Origin": BASE,
    "X-Requested-With": "XMLHttpRequest",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-Dest": "empty",
}

# Pausa entre llamadas (s) para no gatillar el rate-limit del WAF.
PAUSA = 0.45
# Reintentos por llamada (backoff lineal).
REINTENTOS = 5


class OnpeClient:
    def __init__(self, pausa=PAUSA, reintentos=REINTENTOS, verbose=True):
        self.s = requests.Session()
        self.s.headers.update(_HEADERS)
        self.pausa = pausa
        self.reintentos = reintentos
        self.verbose = verbose
        self._warmed = False

    def _warmup(self):
        """Visita la home para tomar cookies del WAF antes de pegarle a la API."""
        for _ in range(3):
            try:
                self.s.get(BASE + "/", timeout=30)
                self._warmed = True
                time.sleep(1.0)
                return
            except requests.RequestException:
                time.sleep(2.0)

    def get_json(self, path):
        """GET a un path del backend; devuelve el dict JSON o None."""
        if not self._warmed:
            self._warmup()
        for intento in range(self.reintentos):
            try:
                r = self.s.get(BASE + path, timeout=30)
                ct = r.headers.get("content-type", "")
                if r.status_code == 200 and ct.startswith("application/json"):
                    time.sleep(self.pausa)
                    return r.json()
                # 200 con HTML (SPA) o 403 → posible rate-limit; backoff y reintento.
            except requests.RequestException:
                pass
            espera = 2.0 * (intento + 1)
            if self.verbose:
                print(f"  [retry {intento+1}/{self.reintentos}] {path[:70]} (espera {espera:.0f}s)")
            time.sleep(espera)
        return None

    # ---- Endpoints concretos ----
    def departamentos(self):
        j = self.get_json(
            f"/presentacion-backend/ubigeos/departamentos?idEleccion={ID_ELECCION}&idAmbitoGeografico=1")
        return (j or {}).get("data") or []

    def totales_departamento(self, ubigeo):
        j = self.get_json(
            f"/presentacion-backend/resumen-general/totales?idEleccion={ID_ELECCION}"
            f"&tipoFiltro=ubigeo_nivel_01&idAmbitoGeografico=1&idUbigeoDepartamento={ubigeo}")
        return (j or {}).get("data")

    def participantes_departamento(self, ubigeo):
        j = self.get_json(
            f"/presentacion-backend/resumen-general/participantes?idEleccion={ID_ELECCION}"
            f"&tipoFiltro=ubigeo_nivel_01&idAmbitoGeografico=1&idUbigeoDepartamento={ubigeo}")
        return (j or {}).get("data")

    def totales_extranjero(self):
        j = self.get_json(
            f"/presentacion-backend/resumen-general/totales?idEleccion={ID_ELECCION}"
            f"&tipoFiltro=ambito_geografico&idAmbitoGeografico=2")
        return (j or {}).get("data")

    def participantes_extranjero(self):
        j = self.get_json(
            f"/presentacion-backend/resumen-general/participantes?idEleccion={ID_ELECCION}"
            f"&tipoFiltro=ambito_geografico&idAmbitoGeografico=2")
        return (j or {}).get("data")
