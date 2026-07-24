"""Recopila ofertas recientes de Bumeran ubicadas en los distritos de Cañete."""

import hashlib
import re
import time
import unicodedata
from datetime import date, timedelta
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from config_canete import DISTRITOS_CANETE
from empleo_utils import asegurar_id
from filtro_fecha import dias_desde_publicacion, es_publicacion_reciente


BASE = "https://www.bumeran.com.pe"
NOMBRES_BUSQUEDA = {
    "SAN VICENTE DE CAÑETE": "san-vicente-de-canete",
    "SAN LUIS": "san-luis-de-canete",
    "SAN ANTONIO": "san-antonio-de-canete",
}
NOMBRES_VALIDACION = {
    "SAN VICENTE DE CAÑETE": "San Vicente de Cañete",
    "SAN LUIS": "San Luis de Cañete",
    "SAN ANTONIO": "San Antonio de Cañete",
}


def crear_driver(headless: bool = True):
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager

    opciones = Options()
    if headless:
        opciones.add_argument("--headless=new")
    opciones.add_argument("--no-sandbox")
    opciones.add_argument("--disable-dev-shm-usage")
    opciones.add_argument("--window-size=1440,1400")
    opciones.add_argument("--lang=es-PE")
    servicio = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=servicio, options=opciones)


def limpiar(texto: object) -> str:
    return re.sub(r"\s+", " ", str(texto or "")).strip()


def normalizar(texto: object) -> str:
    valor = unicodedata.normalize("NFKD", limpiar(texto))
    return "".join(c for c in valor if not unicodedata.combining(c)).casefold()


def slug_distrito(distrito: str) -> str:
    if distrito in NOMBRES_BUSQUEDA:
        return NOMBRES_BUSQUEDA[distrito]
    return re.sub(r"[^a-z0-9]+", "-", normalizar(distrito)).strip("-")


def url_individual(href: str) -> str:
    url = urljoin(BASE, href)
    partes = urlparse(url)
    if partes.hostname != "www.bumeran.com.pe" or not partes.path.startswith("/empleos/") or not partes.path.endswith(".html"):
        return ""
    return f"{partes.scheme}://{partes.netloc}{partes.path}"


def _tarjeta_para(enlace):
    for padre in enlace.parents:
        if padre.name not in {"article", "li", "div"}:
            continue
        texto = limpiar(padre.get_text(" ", strip=True))
        if len(texto) <= 3500 and re.search(r"(publicado|actualizado)\s+(hoy|ayer|hace)", texto, re.I):
            return padre
    return enlace.parent


def extraer_ofertas_html(html: str, distrito: str, limite: int = 10) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    hoy = date.today()
    ofertas = []
    vistos = set()
    nombre_ubicacion = NOMBRES_VALIDACION.get(distrito, distrito.title())

    for enlace in soup.select('a[href*="/empleos/"][href$=".html"]'):
        url = url_individual(enlace.get("href", ""))
        if not url or url in vistos:
            continue
        tarjeta = _tarjeta_para(enlace)
        texto_tarjeta = limpiar(tarjeta.get_text(" ", strip=True))
        if normalizar(nombre_ubicacion) not in normalizar(texto_tarjeta):
            continue
        antiguedad_match = re.search(
            r"(?:publicado|actualizado)\s+(?:hoy|ayer|hace\s+(?:\d+\s+)?(?:minutos?|horas?|d[ií]as?|semanas?|mes(?:es)?))",
            texto_tarjeta,
            re.I,
        )
        antiguedad = limpiar(antiguedad_match.group(0) if antiguedad_match else "")
        if not es_publicacion_reciente(antiguedad):
            continue
        fecha_publicacion = hoy - timedelta(days=dias_desde_publicacion(antiguedad) or 0)

        titulo_nodo = tarjeta.select_one("h2, h3")
        titulo = limpiar(
            titulo_nodo.get_text(" ", strip=True) if titulo_nodo else enlace.get("title") or enlace.get_text(" ", strip=True)
        )
        if not titulo:
            continue
        empresa_nodo = tarjeta.select_one('[data-testid*="company"], .company, [class*="company"]')
        entidad = limpiar(empresa_nodo.get_text(" ", strip=True) if empresa_nodo else "") or "Empresa no especificada"
        referencia = hashlib.sha256(url.encode("utf-8")).hexdigest()[:10].upper()
        ofertas.append(asegurar_id({
            "titulo": titulo,
            "entidad": entidad,
            "ubicacion": f"{nombre_ubicacion}, Lima",
            "departamento": "LIMA",
            "provincia": "CAÑETE",
            "distrito": distrito,
            "numero_convocatoria": f"BU-{referencia}",
            "vacantes": "1",
            "remuneracion": "No especificado",
            "fecha_inicio": fecha_publicacion.strftime("%d/%m/%Y"),
            "fecha_fin": (fecha_publicacion + timedelta(days=7)).strftime("%d/%m/%Y"),
            "fuente": "Bumeran Perú",
            "url_oficial": url,
            "url_postulacion": url,
            "detalle_entidad": antiguedad,
        }))
        vistos.add(url)
        if len(ofertas) >= limite:
            break
    return ofertas


def recopilar_bumeran(headless: bool = True, limite_por_distrito: int = 10) -> list[dict]:
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait

    driver = crear_driver(headless=headless)
    recopiladas = {}
    try:
        for distrito in DISTRITOS_CANETE:
            url = f"{BASE}/empleos-en-{slug_distrito(distrito)}-lima.html"
            print(f"Buscando ofertas de Bumeran en {distrito.title()}...")
            driver.get(url)
            WebDriverWait(driver, 20).until(
                lambda d: d.find_elements(By.CSS_SELECTOR, 'a[href*="/empleos/"]')
                or "captcha" in d.page_source.casefold()
            )
            nuevas = extraer_ofertas_html(driver.page_source, distrito, limite=limite_por_distrito)
            print(f"  {len(nuevas)} ofertas válidas de los últimos 7 días")
            for oferta in nuevas:
                recopiladas[oferta["url_oficial"]] = oferta
            time.sleep(1)
    finally:
        driver.quit()
    return list(recopiladas.values())
