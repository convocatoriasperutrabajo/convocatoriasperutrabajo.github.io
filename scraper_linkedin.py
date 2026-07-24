"""Recopila ofertas públicas de LinkedIn ubicadas en los distritos de Cañete."""

import hashlib
import re
import time
import unicodedata
from datetime import date, timedelta
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from config_canete import DISTRITOS_CANETE
from empleo_utils import asegurar_id


BASE = "https://pe.linkedin.com"
URL_BUSQUEDA = (
    f"{BASE}/jobs/search?keywords=&location=Provincia%20de%20Ca%C3%B1ete%2C%20Lima%2C%20Per%C3%BA"
    "&geoId=106443255&position=1&pageNum=0"
)
NOMBRES_DISTRITOS = {
    distrito: distrito.title()
    for distrito in DISTRITOS_CANETE
}
NOMBRES_DISTRITOS.update({
    "SAN VICENTE DE CAÑETE": "San Vicente de Cañete",
    "SAN LUIS": "San Luis de Cañete",
    "SAN ANTONIO": "San Antonio de Cañete",
})


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
    opciones.add_argument("--window-size=1440,1600")
    opciones.add_argument("--lang=es-PE")
    servicio = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=servicio, options=opciones)


def limpiar(texto: object) -> str:
    return re.sub(r"\s+", " ", str(texto or "")).strip()


def normalizar(texto: object) -> str:
    valor = unicodedata.normalize("NFKD", limpiar(texto))
    return "".join(c for c in valor if not unicodedata.combining(c)).casefold()


def detectar_distrito(ubicacion: str, titulo: str = "") -> str:
    contenido = normalizar(f"{ubicacion} {titulo}")
    for distrito, nombre in NOMBRES_DISTRITOS.items():
        if normalizar(nombre) in contenido:
            return distrito
    return ""


def url_individual(href: str) -> str:
    url = urljoin(BASE, href)
    partes = urlparse(url)
    if partes.hostname != "pe.linkedin.com" or not partes.path.startswith("/jobs/view/"):
        return ""
    return f"{partes.scheme}://{partes.netloc}{partes.path}".rstrip("/")


def extraer_ofertas_html(html: str, limite: int = 100) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    hoy = date.today()
    ofertas = []
    vistos = set()

    for tarjeta in soup.select("li, .base-card, .job-search-card"):
        enlace = tarjeta.select_one('a.base-card__full-link[href*="/jobs/view/"], a[href*="/jobs/view/"]')
        if not enlace:
            continue
        url = url_individual(enlace.get("href", ""))
        if not url or url in vistos:
            continue
        titulo_nodo = tarjeta.select_one(".base-search-card__title, h3")
        empresa_nodo = tarjeta.select_one(".base-search-card__subtitle, h4")
        ubicacion_nodo = tarjeta.select_one(".job-search-card__location")
        fecha_nodo = tarjeta.select_one("time")
        titulo = limpiar(titulo_nodo.get_text(" ", strip=True) if titulo_nodo else enlace.get_text(" ", strip=True))
        entidad = limpiar(empresa_nodo.get_text(" ", strip=True) if empresa_nodo else "") or "Empresa no especificada"
        ubicacion = limpiar(ubicacion_nodo.get_text(" ", strip=True) if ubicacion_nodo else "")
        distrito = detectar_distrito(ubicacion, titulo)
        if not titulo or not distrito:
            continue

        antiguedad = limpiar(fecha_nodo.get_text(" ", strip=True) if fecha_nodo else "") or "Publicado recientemente"
        referencia = hashlib.sha256(url.encode("utf-8")).hexdigest()[:10].upper()
        ofertas.append(asegurar_id({
            "titulo": titulo,
            "entidad": entidad,
            "ubicacion": ubicacion,
            "departamento": "LIMA",
            "provincia": "CAÑETE",
            "distrito": distrito,
            "numero_convocatoria": f"LI-{referencia}",
            "vacantes": "1",
            "remuneracion": "No especificado",
            "fecha_inicio": hoy.strftime("%d/%m/%Y"),
            "fecha_fin": (hoy + timedelta(days=30)).strftime("%d/%m/%Y"),
            "fuente": "LinkedIn",
            "url_oficial": url,
            "url_postulacion": url,
            "detalle_entidad": antiguedad,
        }))
        vistos.add(url)
        if len(ofertas) >= limite:
            break
    return ofertas


def recopilar_linkedin(headless: bool = True, limite: int = 100) -> list[dict]:
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait

    driver = crear_driver(headless=headless)
    try:
        print("Buscando ofertas de LinkedIn en la provincia de Cañete...")
        driver.get(URL_BUSQUEDA)
        WebDriverWait(driver, 20).until(
            lambda d: d.find_elements(By.CSS_SELECTOR, 'a[href*="/jobs/view/"]')
            or "captcha" in d.page_source.casefold()
        )
        for _ in range(3):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
        ofertas = extraer_ofertas_html(driver.page_source, limite=limite)
        print(f"  {len(ofertas)} ofertas válidas")
        return ofertas
    finally:
        driver.quit()
