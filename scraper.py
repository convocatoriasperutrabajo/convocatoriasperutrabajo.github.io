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
from datetime import datetime, date
from pathlib import Path
from urllib.parse import urlparse

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from empleo_utils import asegurar_id, clave_base_oferta, es_enlace_postulacion_directo
from consola import configurar_salida_utf8

configurar_salida_utf8()

URL = "https://app.servir.gob.pe/DifusionOfertasExterno/faces/consultas/ofertas_laborales.xhtml"
EMPLEOS_JSON = "empleos.json"
CARPETA_DOCUMENTOS = Path("documentos_oficiales")


def crear_driver(headless: bool = True):
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    # Los documentos se descargan desde el botón oficial "Convocatoria en
    # Word". Chrome no muestra diálogos ni pide confirmación en cada archivo.
    carpeta_descargas = str(CARPETA_DOCUMENTOS.resolve())
    options.add_experimental_option("prefs", {
        "download.default_directory": carpeta_descargas,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
    })
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
        partes_ubicacion = [parte.strip() for parte in ubicacion_completa.split(" - ") if parte.strip()]
        departamento = partes_ubicacion[0] if partes_ubicacion else ubicacion_completa
        provincia = partes_ubicacion[1] if len(partes_ubicacion) > 1 else ""
        distrito = partes_ubicacion[2] if len(partes_ubicacion) > 2 else ""

        oferta = {
            "titulo": titulo,
            "entidad": entidad,
            "ubicacion": ubicacion_completa,
            "departamento": departamento,
            "provincia": provincia,
            "distrito": distrito,
            "numero_convocatoria": limpio(convocatoria_match),
            "vacantes": limpio(vacantes_match),
            "remuneracion": limpio(remuneracion_match),
            "fecha_inicio": fecha_inicio_match.group(1) if fecha_inicio_match else "",
            "fecha_fin": fecha_fin_match.group(1) if fecha_fin_match else "",
            "fuente": "SERVIR - Talento Perú",
            "url_oficial": URL,
        }

        if oferta["titulo"] and len(oferta["titulo"]) > 3 and oferta["numero_convocatoria"]:
            ofertas.append(oferta)

    return ofertas


SECCIONES_DETALLE = (
    ("requerimiento", "REQUERIMIENTO:", "EXPERIENCIA:"),
    ("experiencia", "EXPERIENCIA:", "FORMACIÓN ACADÉMICA - PERFIL:"),
    ("formacion_academica", "FORMACIÓN ACADÉMICA - PERFIL:", "ESPECIALIZACIÓN:"),
    ("especializacion", "ESPECIALIZACIÓN:", "CONOCIMIENTO:"),
    ("conocimiento", "CONOCIMIENTO:", "COMPETENCIAS:"),
    ("competencias", "COMPETENCIAS:", "DETALLE:"),
    ("detalle_entidad", "DETALLE:", "CANTIDAD DE VACANTES:"),
)


def extraer_secciones_detalle(texto: str) -> dict:
    """Extrae los requisitos que SERVIR muestra al abrir «¡Ver más!»."""
    texto = re.sub(r"\s+", " ", texto).strip()
    resultado = {}
    for campo, inicio, fin in SECCIONES_DETALLE:
        patron = rf"{re.escape(inicio)}\s*(.*?)\s*(?={re.escape(fin)})"
        coincidencia = re.search(patron, texto, re.IGNORECASE)
        if coincidencia:
            valor = coincidencia.group(1).strip(" -")
            if valor and valor.upper() != "NO APLICA":
                resultado[campo] = valor
    return resultado


def es_enlace_de_bases(url: str, texto: str) -> bool:
    """Reconoce documentos o enlaces que la entidad nombra como bases/anexos."""
    texto_enlace = f"{url} {texto}".lower()
    return bool(
        re.search(r"\.(pdf|doc|docx|xls|xlsx)(?:$|[?#])", texto_enlace)
        or any(palabra in texto_enlace for palabra in ("base", "anexo", "cronograma"))
    )


def extraer_detalle_abierto(driver) -> dict:
    """Lee requisitos y el enlace declarado por la entidad en la ficha abierta."""
    formulario = WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.ID, "frmDetaOferLabo"))
    )
    resultado = extraer_secciones_detalle(formulario.text)
    codigo = re.search(r"\bN[°º]\s*(\d{4,})\b", formulario.text, re.IGNORECASE)
    if codigo:
        resultado["codigo_servir"] = codigo.group(1)

    enlaces_bases = []
    for enlace in formulario.find_elements(By.CSS_SELECTOR, "a[href]"):
        href = (enlace.get_attribute("href") or "").strip()
        texto_enlace = (enlace.text or "").strip()
        partes = urlparse(href)
        host = (partes.hostname or "").lower()
        if partes.scheme not in {"http", "https"} or not host or host.endswith("servir.gob.pe"):
            continue
        if es_enlace_de_bases(href, texto_enlace):
            enlaces_bases.append({
                "titulo": texto_enlace or "Descargar bases o anexo oficial",
                "url": href,
            })
        elif es_enlace_postulacion_directo(href) and not resultado.get("url_postulacion"):
            resultado["url_postulacion"] = href
        elif not resultado.get("url_consulta"):
            resultado["url_consulta"] = href
    if enlaces_bases:
        resultado["enlaces_bases"] = enlaces_bases

    return resultado


def volver_al_listado(driver, numero_pagina: int) -> None:
    """Recarga el listado oficial y restaura la pagina que se estaba leyendo.

    SERVIR puede dejar una capa de carga activa si se usa el historial para
    volver desde una ficha. Recargar el listado evita interactuar con esa capa
    y mantiene la navegacion normal del portal.
    """
    driver.get(URL)
    WebDriverWait(driver, 25).until(
        lambda d: len(d.find_elements(By.CSS_SELECTOR, "button[title*='Ver m']")) > 0
    )
    for _ in range(1, numero_pagina):
        if not hacer_click_siguiente(driver):
            raise RuntimeError(f"No se pudo restaurar la pagina {numero_pagina} de SERVIR")


def enriquecer_ofertas_pagina(driver, ofertas: list[dict], numero_pagina: int) -> None:
    """Visita cada ficha para leer requisitos y enlaces oficiales de la entidad."""
    for indice, oferta in enumerate(ofertas):
        WebDriverWait(driver, 20).until(
            lambda d: len(d.find_elements(By.CSS_SELECTOR, "button[title*='Ver m']")) > indice
        )
        botones = driver.find_elements(By.CSS_SELECTOR, "button[title*='Ver m']")
        try:
            boton = botones[indice]
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", boton)
            WebDriverWait(driver, 15).until(EC.element_to_be_clickable(boton))
            boton.click()
            WebDriverWait(driver, 20).until(
                lambda d: "detalle_ofertas_laborales.xhtml" in d.current_url
            )
            oferta.update(extraer_detalle_abierto(driver))
            if oferta.get("url_postulacion"):
                print(f"   Enlace de entidad: {oferta['url_postulacion']}")
            else:
                print(f"   Sin enlace específico: {oferta['titulo']}")
        finally:
            if "detalle_ofertas_laborales.xhtml" in driver.current_url:
                volver_al_listado(driver, numero_pagina)


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
    with open(EMPLEOS_JSON, "w", encoding="utf-8", newline="\n") as f:
        json.dump(lista, f, ensure_ascii=False, indent=2)


def retirar_ofertas_vencidas(empleos: dict, hoy: date | None = None) -> int:
    """Retira del sitio convocatorias cuya fecha de cierre ya pasó."""
    hoy = hoy or date.today()
    vencidas = []
    for identificador, oferta in empleos.items():
        fecha_fin = str(oferta.get("fecha_fin", "")).strip()
        try:
            cierre = datetime.strptime(fecha_fin, "%d/%m/%Y").date()
        except ValueError:
            continue
        if cierre < hoy:
            vencidas.append(identificador)

    for identificador in vencidas:
        empleos.pop(identificador, None)
    return len(vencidas)


def retirar_duplicados_sin_codigo(empleos: dict) -> int:
    """Elimina el registro antiguo si ya existen perfiles con código SERVIR."""
    bases_con_codigo = {
        clave_base_oferta(oferta)
        for oferta in empleos.values()
        if oferta.get("codigo_servir")
    }
    duplicados = [
        identificador
        for identificador, oferta in empleos.items()
        if not oferta.get("codigo_servir") and clave_base_oferta(oferta) in bases_con_codigo
    ]
    for identificador in duplicados:
        empleos.pop(identificador, None)
    return len(duplicados)


def esperar_descarga(archivos_antes: set[Path], timeout_segundos: int = 45):
    """Devuelve el archivo terminado que acaba de descargar Chrome."""
    limite = time.time() + timeout_segundos
    while time.time() < limite:
        nuevos = [p for p in CARPETA_DOCUMENTOS.iterdir() if p not in archivos_antes]
        terminados = [p for p in nuevos if p.is_file() and not p.name.endswith(".crdownload")]
        if terminados and not any(p.name.endswith(".crdownload") for p in nuevos):
            return max(terminados, key=lambda p: p.stat().st_mtime)
        time.sleep(1)
    return None


def extension_documento(archivo: Path) -> str:
    """SERVIR a veces descarga un .tmp que realmente es un .docx (ZIP)."""
    if archivo.suffix.lower() == ".tmp":
        try:
            if archivo.read_bytes()[:4] == b"PK\x03\x04":
                return ".docx"
        except OSError:
            pass
    return archivo.suffix.lower() or ".docx"


def normalizar_documentos_existentes(empleos: dict) -> int:
    """Corrige extensiones temporales ya asociadas a convocatorias."""
    corregidos = 0
    for oferta in empleos.values():
        ruta = oferta.get("archivo_oficial")
        if not ruta:
            continue
        archivo = Path(ruta)
        if archivo.exists() and archivo.suffix.lower() == ".tmp":
            destino = archivo.with_suffix(extension_documento(archivo))
            if destino != archivo:
                archivo.replace(destino)
                oferta["archivo_oficial"] = destino.as_posix()
                corregidos += 1
    return corregidos


def descargar_documentos_pagina(driver, ofertas: list[dict], empleos: dict, restantes: int) -> int:
    """Guarda los Word oficiales faltantes y devuelve cuántos se descargaron."""
    if restantes <= 0:
        return 0

    botones = driver.find_elements(By.CSS_SELECTOR, "button[title='Convocatoria en Word']")
    descargados = 0
    for indice, oferta_sin_id in enumerate(ofertas):
        if descargados >= restantes or indice >= len(botones):
            break

        oferta = asegurar_id(oferta_sin_id)
        previo = empleos.get(oferta["id"], {})
        archivo_relativo = previo.get("archivo_oficial") or oferta.get("archivo_oficial")
        if archivo_relativo and Path(archivo_relativo).exists():
            oferta_sin_id["archivo_oficial"] = archivo_relativo
            continue

        antes = set(CARPETA_DOCUMENTOS.iterdir())
        try:
            # Se vuelve a localizar porque el DOM puede refrescarse después de
            # una descarga anterior.
            botones = driver.find_elements(By.CSS_SELECTOR, "button[title='Convocatoria en Word']")
            botones[indice].click()
            archivo = esperar_descarga(antes)
            if not archivo:
                print(f"   No se descargó el Word de: {oferta['titulo']}")
                continue

            destino = CARPETA_DOCUMENTOS / f"{oferta['id']}{extension_documento(archivo)}"
            if archivo != destino:
                if destino.exists():
                    destino.unlink()
                archivo.replace(destino)
            oferta_sin_id["archivo_oficial"] = destino.as_posix()
            descargados += 1
            print(f"   Word oficial guardado: {destino.name}")
        except Exception as e:
            print(f"   No se pudo descargar el Word de '{oferta['titulo']}': {e}")
    return descargados


def ejecutar_scraper(max_paginas: int = None, headless: bool = True, pausa_segundos: float = 1.5,
                     max_documentos: int = 0):
    empleos = cargar_empleos_existentes()
    total_antes = len(empleos)
    CARPETA_DOCUMENTOS.mkdir(exist_ok=True)
    documentos_corregidos = normalizar_documentos_existentes(empleos)
    documentos_descargados = 0

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
            if not ofertas:
                raise RuntimeError(
                    "SERVIR no devolvió convocatorias. El portal pudo cambiar o bloquear la consulta."
                )

            enriquecer_ofertas_pagina(driver, ofertas, pagina_actual)

            documentos_descargados += descargar_documentos_pagina(
                driver, ofertas, empleos, max_documentos - documentos_descargados
            )

            # El número puede repetirse entre entidades; el ID también toma
            # entidad, puesto y ubicación para impedir falsos duplicados.
            for oferta in ofertas:
                oferta = asegurar_id(oferta)
                anterior = empleos.get(oferta["id"], {})
                for campo in (
                    "archivo_oficial", "url_postulacion", "url_consulta", "requerimiento", "experiencia",
                    "formacion_academica", "especializacion", "conocimiento",
                    "competencias", "detalle_entidad", "enlaces_bases",
                ):
                    if campo in anterior and campo not in oferta:
                        oferta[campo] = anterior[campo]
                empleos[oferta["id"]] = oferta

            if max_paginas and pagina_actual >= max_paginas:
                print(f"\nLímite de páginas de prueba alcanzado ({max_paginas}).")
                break

            num_actual, num_total = obtener_numero_pagina_actual(driver)
            if num_total and num_actual and num_actual >= num_total:
                print("\nSe llegó a la última página.")
                break

            if not hacer_click_siguiente(driver):
                if num_total and num_actual and num_actual < num_total:
                    raise RuntimeError(
                        f"La paginación se detuvo en {num_actual} de {num_total}; no se guardará una actualización incompleta."
                    )
                print("\nNo se pudo avanzar más; se considera el final de la paginación.")
                break

            pagina_actual += 1
            time.sleep(pausa_segundos)

    finally:
        driver.quit()

    duplicados_retirados = retirar_duplicados_sin_codigo(empleos)
    ofertas_vencidas = retirar_ofertas_vencidas(empleos)
    guardar_empleos(empleos)

    print("\n================ RESUMEN ================")
    print(f"Ofertas antes de esta corrida: {total_antes}")
    print(f"Ofertas nuevas encontradas:    {len(empleos) - total_antes}")
    print(f"Documentos oficiales bajados:  {documentos_descargados}")
    if documentos_corregidos:
        print(f"Extensiones de Word corregidas: {documentos_corregidos}")
    print(f"Total acumulado en empleos.json: {len(empleos)}")
    if ofertas_vencidas:
        print(f"Ofertas vencidas retiradas:      {ofertas_vencidas}")
    if duplicados_retirados:
        print(f"Registros antiguos combinados:  {duplicados_retirados}")
    print("===========================================")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Actualizador de ofertas laborales")
    parser.add_argument("--max-paginas", type=int, default=None)
    parser.add_argument("--visible", action="store_true")
    parser.add_argument("--servir", action="store_true",
                        help="usa excepcionalmente la fuente anterior de SERVIR")
    parser.add_argument("--max-documentos", type=int, default=0,
                        help="máximo de Word oficiales a bajar por ejecución (0 = ninguno)")
    parser.add_argument("--normalizar-documentos", action="store_true",
                        help="corrige extensiones temporales de Word y termina")
    args = parser.parse_args()

    if args.normalizar_documentos:
        empleos = cargar_empleos_existentes()
        corregidos = normalizar_documentos_existentes(empleos)
        guardar_empleos(empleos)
        print(f"Extensiones de Word corregidas: {corregidos}")
    elif args.servir:
        ejecutar_scraper(max_paginas=args.max_paginas, headless=not args.visible,
                         max_documentos=args.max_documentos)
    else:
        from scraper_computrabajo import ejecutar_computrabajo
        ejecutar_computrabajo(headless=not args.visible)
