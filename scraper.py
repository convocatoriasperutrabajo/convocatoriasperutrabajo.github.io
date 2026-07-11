"""
scraper.py
Recorre las páginas del portal oficial de Talento Perú (SERVIR) y guarda
cada oferta en empleos.json, evitando duplicados (por numero_convocatoria).

Uso:
    python scraper.py                  -> recorre todas las páginas
    python scraper.py --max-paginas 5  -> solo las primeras 5 (para pruebas)
"""
import re
import os
import json
import time
import argparse

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from empleo_utils import asegurar_id
from consola import configurar_salida_utf8

configurar_salida_utf8()

URL = "https://app.servir.gob.pe/DifusionOfertasExterno/faces/consultas/ofertas_laborales.xhtml"
EMPLEOS_JSON = "empleos.json"


def crear_driver(headless: bool = True):
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(60)
    return driver


def extraer_ofertas_de_texto(texto: str):
    """Parsea el texto plano de la página usando los patrones de campo fijos."""
    ofertas = []
    bloques = re.split(r'Ubicación:\s*', texto)

    for i in range(1, len(bloques)):
        bloque_anterior = bloques[i - 1]
        bloque_actual = bloques[i]

        lineas_anteriores = [l.strip() for l in bloque_anterior.split('\n') if l.strip()]
        titulo = lineas_anteriores[-2] if len(lineas_anteriores) >= 2 else ""
        entidad = lineas_anteriores[-1] if len(lineas_anteriores) >= 1 else ""

        ubicacion_match = re.search(r'^(.*?)Número de Convocatoria', bloque_actual, re.DOTALL)
        convocatoria_match = re.search(r'Número de Convocatoria:\s*(.*?)Cantidad de Vacantes', bloque_actual, re.DOTALL)
        vacantes_match = re.search(r'Cantidad de Vacantes:\s*(.*?)Remuneración', bloque_actual, re.DOTALL)
        remuneracion_match = re.search(r'Remuneración:\s*(.*?)Fecha Inicio', bloque_actual, re.DOTALL)
        fecha_inicio_match = re.search(r'Publicación:\s*(\d{2}/\d{2}/\d{4})', bloque_actual)
        fecha_fin_match = re.search(r'Fecha Fin de Publicación:\s*(\d{2}/\d{2}/\d{4})', bloque_actual)

        def limpio(m):
            return re.sub(r'\s+', ' ', m.group(1)).strip() if m else ""

        ubicacion_completa = limpio(ubicacion_match)
        departamento = ubicacion_completa.split(" - ")[0].strip() if " - " in ubicacion_completa else ubicacion_completa

        oferta = {
            "titulo": titulo,
            "entidad": entidad,
            "ubicacion": ubicacion_completa,
            "departamento": departamento,
            "numero_convocatoria": limpio(convocatoria_match),
            "vacantes": limpio(vacantes_match),
            "remuneracion": limpio(remuneracion_match),
            "fecha_inicio": fecha_inicio_match.group(1) if fecha_inicio_match else "",
            "fecha_fin": fecha_fin_match.group(1) if fecha_fin_match else "",
        }

        if oferta["titulo"] and len(oferta["titulo"]) > 3 and oferta["numero_convocatoria"]:
            ofertas.append(oferta)

    return ofertas


def obtener_numero_pagina_actual(driver):
    try:
        texto = driver.find_element(By.XPATH, "//*[contains(text(),'Página') and contains(text(),'de')]").text
        m = re.search(r'Página\s+(\d+)\s+de\s+(\d+)', texto)
        if m:
            return int(m.group(1)), int(m.group(2))
    except Exception:
        pass
    return None, None


def hacer_click_siguiente(driver) -> bool:
    try:
        link_siguiente = driver.find_element(By.PARTIAL_LINK_TEXT, "Sig.")
        clases = link_siguiente.get_attribute("class") or ""
        if "disabled" in clases.lower():
            return False

        try:
            primer_elemento_anterior = driver.find_elements(By.CSS_SELECTOR, "tr, .ui-panel")[0]
        except Exception:
            primer_elemento_anterior = None

        link_siguiente.click()
        time.sleep(2.5)

        if primer_elemento_anterior is not None:
            try:
                WebDriverWait(driver, 15).until(EC.staleness_of(primer_elemento_anterior))
            except Exception:
                pass

        return True
    except Exception as e:
        print(f"   No se pudo hacer click en 'Sig.': {e}")
        return False


def cargar_empleos_existentes():
    if os.path.exists(EMPLEOS_JSON):
        with open(EMPLEOS_JSON, "r", encoding="utf-8") as f:
            lista = json.load(f)
            lista_con_id = [asegurar_id(o) for o in lista]
            return {o["id"]: o for o in lista_con_id}
    return {}


def guardar_empleos(diccionario_por_numero):
    lista = list(diccionario_por_numero.values())
    # Más recientes primero (por fecha de inicio de publicación cuando se pueda comparar)
    with open(EMPLEOS_JSON, "w", encoding="utf-8") as f:
        json.dump(lista, f, ensure_ascii=False, indent=2)


def ejecutar_scraper(max_paginas: int = None, headless: bool = True, pausa_segundos: float = 1.5):
    empleos = cargar_empleos_existentes()
    total_antes = len(empleos)

    driver = crear_driver(headless=headless)
    pagina_actual = 1

    try:
        print(f"Conectando a {URL} ...")
        driver.get(URL)

        WebDriverWait(driver, 25).until(
            lambda d: len(d.find_elements(By.CSS_SELECTOR, "tr, td, a")) > 0
        )

        while True:
            print(f"\n--- Procesando página {pagina_actual} ---")
            soup = BeautifulSoup(driver.page_source, "html.parser")
            ofertas = extraer_ofertas_de_texto(soup.get_text())
            print(f"   {len(ofertas)} ofertas detectadas en esta página")

            # El número puede repetirse entre entidades; el ID también toma
            # entidad, puesto y ubicación para impedir falsos duplicados.
            for oferta in ofertas:
                oferta = asegurar_id(oferta)
                empleos[oferta["id"]] = oferta

            if max_paginas and pagina_actual >= max_paginas:
                print(f"\nLímite de páginas de prueba alcanzado ({max_paginas}).")
                break

            num_actual, num_total = obtener_numero_pagina_actual(driver)
            if num_total and num_actual and num_actual >= num_total:
                print("\nSe llegó a la última página.")
                break

            if not hacer_click_siguiente(driver):
                print("\nNo se pudo avanzar más (fin de la paginación o error).")
                break

            pagina_actual += 1
            time.sleep(pausa_segundos)

    except Exception as e:
        print(f"Error durante el scraping: {e}")
    finally:
        driver.quit()

    guardar_empleos(empleos)

    print("\n================ RESUMEN ================")
    print(f"Ofertas antes de esta corrida: {total_antes}")
    print(f"Ofertas nuevas encontradas:    {len(empleos) - total_antes}")
    print(f"Total acumulado en empleos.json: {len(empleos)}")
    print("===========================================")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scraper de Talento Perú (SERVIR)")
    parser.add_argument("--max-paginas", type=int, default=None)
    parser.add_argument("--visible", action="store_true")
    args = parser.parse_args()

    ejecutar_scraper(max_paginas=args.max_paginas, headless=not args.visible)
