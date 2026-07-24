"""Recopila avisos recientes de Computrabajo para la provincia de Cañete."""
import hashlib
import json
import re
import time
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from empleo_utils import asegurar_id


BASE = "https://pe.computrabajo.com"
ARCHIVO = Path("empleos.json")
ZONAS = {
    "Mala": f"{BASE}/empleos-en-lima-en-mala",
    "Chilca": f"{BASE}/empleos-en-lima-en-chilca",
    "Asia": f"{BASE}/empleos-en-lima-en-asia",
    "San Vicente de Cañete": f"{BASE}/empleos-en-lima-en-san-vicente-de-canete",
}
LOCALIDADES_ADMITIDAS = ("mala", "chilca", "asia", "san vicente de cañete", "cañete")


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
    servicio = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=servicio, options=opciones)


def limpiar(texto: object) -> str:
    return re.sub(r"\s+", " ", str(texto or "")).strip()


def extraer_ofertas_html(html: str, limite: int = 12) -> list[dict]:
    """Convierte las tarjetas visibles en registros con enlace individual."""
    soup = BeautifulSoup(html, "html.parser")
    hoy = date.today()
    ofertas = []
    vistos = set()
    for tarjeta in soup.select("article"):
        enlace = tarjeta.select_one('h2 a[href*="/ofertas-de-trabajo/"]')
        if not enlace:
            continue
        url = urljoin(BASE, enlace.get("href", "")).split("#", 1)[0]
        titulo = limpiar(enlace.get_text(" ", strip=True))
        textos = [limpiar(p.get_text(" ", strip=True)) for p in tarjeta.select("p")]
        ubicacion = next(
            (texto for texto in textos if "," in texto and any(z in texto.casefold() for z in LOCALIDADES_ADMITIDAS)),
            "",
        )
        if not titulo or not ubicacion or url in vistos:
            continue
        vistos.add(url)
        empresa_enlace = tarjeta.select_one('a[href*="/empresas/"]')
        entidad = limpiar(empresa_enlace.get_text(" ", strip=True)) if empresa_enlace else ""
        if not entidad:
            entidad = next(
                (texto for texto in textos if texto and texto != ubicacion and not texto.lower().startswith("hace ")),
                "Empresa no especificada",
            )
        salario = next((limpiar(x) for x in tarjeta.stripped_strings if "S/." in x), "No especificado")
        antiguedad = next(
            (texto for texto in textos if texto.lower().startswith(("hace ", "ayer", "hoy"))),
            "Publicado recientemente",
        )
        referencia = hashlib.sha256(url.encode("utf-8")).hexdigest()[:10].upper()
        oferta = asegurar_id({
            "titulo": titulo,
            "entidad": entidad,
            "ubicacion": ubicacion,
            "departamento": "LIMA",
            "provincia": "CAÑETE",
            "distrito": ubicacion.split(",", 1)[0].strip().upper(),
            "numero_convocatoria": f"CT-{referencia}",
            "vacantes": "1",
            "remuneracion": salario,
            "fecha_inicio": hoy.strftime("%d/%m/%Y"),
            "fecha_fin": (hoy + timedelta(days=30)).strftime("%d/%m/%Y"),
            "fuente": "Computrabajo Perú",
            "url_oficial": url,
            "url_postulacion": url,
            "detalle_entidad": antiguedad,
        })
        ofertas.append(oferta)
        if len(ofertas) >= limite:
            break
    return ofertas


def guardar_si_hay_resultados(ofertas: list[dict]) -> None:
    if not ofertas:
        raise RuntimeError(
            "Computrabajo no devolvió ofertas. Se conserva la publicación anterior para no dejar la web vacía."
        )
    ARCHIVO.write_text(
        json.dumps(ofertas, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def ejecutar_computrabajo(headless: bool = True, limite_por_zona: int = 12) -> None:
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait

    driver = crear_driver(headless=headless)
    recopiladas = {}
    try:
        for zona, url in ZONAS.items():
            print(f"Buscando ofertas en {zona}...")
            driver.get(url)
            WebDriverWait(driver, 20).until(
                lambda d: d.find_elements(By.CSS_SELECTOR, "article")
                or "robot" in d.page_source.lower()
            )
            nuevas = extraer_ofertas_html(driver.page_source, limite=limite_por_zona)
            print(f"  {len(nuevas)} ofertas válidas")
            for oferta in nuevas:
                recopiladas[oferta["url_oficial"]] = oferta
            time.sleep(1)
    finally:
        driver.quit()
    guardar_si_hay_resultados(list(recopiladas.values()))
    print(f"✅ {len(recopiladas)} ofertas locales guardadas")
