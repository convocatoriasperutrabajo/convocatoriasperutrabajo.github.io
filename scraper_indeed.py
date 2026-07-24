"""Recopila avisos individuales de Indeed ubicados en la provincia de Cañete."""

import hashlib
import re
import time
import unicodedata
from datetime import date, timedelta
from urllib.parse import parse_qs, quote_plus, urljoin, urlparse

from bs4 import BeautifulSoup

from config_canete import DISTRITOS_CANETE
from empleo_utils import asegurar_id
from filtro_fecha import dias_desde_publicacion, es_publicacion_reciente


BASE = "https://pe.indeed.com"
LUGARES_BUSQUEDA = {
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
    opciones.add_argument("--window-size=1440,1200")
    opciones.add_argument("--lang=es-PE")
    opciones.add_argument("--disable-blink-features=AutomationControlled")
    servicio = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=servicio, options=opciones)


def limpiar(texto: object) -> str:
    return re.sub(r"\s+", " ", str(texto or "")).strip()


def normalizar(texto: object) -> str:
    valor = unicodedata.normalize("NFKD", limpiar(texto))
    return "".join(c for c in valor if not unicodedata.combining(c)).casefold()


def url_individual(href: str) -> str:
    url = urljoin(BASE, href)
    codigo = parse_qs(urlparse(url).query).get("jk", [""])[0]
    return f"{BASE}/viewjob?jk={codigo}" if codigo else ""


def extraer_ofertas_html(html: str, distrito: str, limite: int = 10) -> list[dict]:
    """Extrae solamente tarjetas cuya ubicación coincide con el distrito solicitado."""
    soup = BeautifulSoup(html, "html.parser")
    hoy = date.today()
    ofertas = []
    vistos = set()
    lugar_buscado = LUGARES_BUSQUEDA.get(distrito, distrito.title())
    claves_ubicacion = {normalizar(distrito), normalizar(lugar_buscado)}

    for enlace in soup.select("a[data-jk], a.jcs-JobTitle, h2.jobTitle a"):
        url = url_individual(enlace.get("href", ""))
        if not url or url in vistos:
            continue
        tarjeta = enlace.find_parent(
            lambda tag: tag.name in {"div", "li"} and (
                "job_seen_beacon" in (tag.get("class") or [])
                or tag.get("data-testid") == "slider_item"
                or "result" in " ".join(tag.get("class") or []).casefold()
            )
        ) or enlace.parent
        ubicacion_nodo = tarjeta.select_one(
            '[data-testid="text-location"], .companyLocation, [data-testid="job-location"]'
        )
        ubicacion = limpiar(ubicacion_nodo.get_text(" ", strip=True) if ubicacion_nodo else "")
        ubicacion_normalizada = normalizar(ubicacion)
        if not ubicacion or not any(clave in ubicacion_normalizada for clave in claves_ubicacion):
            continue

        titulo = limpiar(enlace.get_text(" ", strip=True))
        empresa_nodo = tarjeta.select_one('[data-testid="company-name"], .companyName, [data-testid="companyName"]')
        entidad = limpiar(empresa_nodo.get_text(" ", strip=True) if empresa_nodo else "") or "Empresa no especificada"
        salario_nodo = tarjeta.select_one(
            '.salary-snippet-container, .salaryText, [data-testid="attribute_snippet_testid"]'
        )
        salario = limpiar(salario_nodo.get_text(" ", strip=True) if salario_nodo else "") or "No especificado"
        fecha_nodo = tarjeta.select_one(".date, [data-testid='myJobsStateDate']")
        antiguedad = limpiar(fecha_nodo.get_text(" ", strip=True) if fecha_nodo else "") or "Publicado recientemente"
        if not es_publicacion_reciente(antiguedad):
            continue
        fecha_publicacion = hoy - timedelta(days=dias_desde_publicacion(antiguedad) or 0)
        referencia = hashlib.sha256(url.encode("utf-8")).hexdigest()[:10].upper()
        ofertas.append(asegurar_id({
            "titulo": titulo,
            "entidad": entidad,
            "ubicacion": ubicacion,
            "departamento": "LIMA",
            "provincia": "CAÑETE",
            "distrito": distrito,
            "numero_convocatoria": f"IN-{referencia}",
            "vacantes": "1",
            "remuneracion": salario,
            "fecha_inicio": fecha_publicacion.strftime("%d/%m/%Y"),
            "fecha_fin": (fecha_publicacion + timedelta(days=7)).strftime("%d/%m/%Y"),
            "fuente": "Indeed Perú",
            "url_oficial": url,
            "url_postulacion": url,
            "detalle_entidad": antiguedad,
        }))
        vistos.add(url)
        if len(ofertas) >= limite:
            break
    return ofertas


def recopilar_indeed(headless: bool = True, limite_por_distrito: int = 10) -> list[dict]:
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait

    driver = crear_driver(headless=headless)
    recopiladas = {}
    try:
        for distrito in DISTRITOS_CANETE:
            lugar = LUGARES_BUSQUEDA.get(distrito, distrito.title())
            url = f"{BASE}/jobs?l={quote_plus(lugar + ', Lima')}&sort=date"
            print(f"Buscando ofertas de Indeed en {lugar}...")
            driver.get(url)
            WebDriverWait(driver, 20).until(
                lambda d: d.find_elements(By.CSS_SELECTOR, "a[data-jk], a.jcs-JobTitle, h2.jobTitle a")
                or "captcha" in d.page_source.casefold()
            )
            nuevas = extraer_ofertas_html(driver.page_source, distrito, limite=limite_por_distrito)
            print(f"  {len(nuevas)} ofertas válidas")
            for oferta in nuevas:
                recopiladas[oferta["url_oficial"]] = oferta
            time.sleep(1)
    finally:
        driver.quit()
    return list(recopiladas.values())
