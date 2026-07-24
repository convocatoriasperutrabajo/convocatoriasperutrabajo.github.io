"""
facebook_poster.py
Publica en tu Página de Facebook las ofertas de empleos.json que aún no
se hayan publicado (registro en publicados_facebook.json).

Configuración (variables de entorno o archivo .env):
    FB_PAGE_ID
    FB_PAGE_ACCESS_TOKEN

Uso:
    python facebook_poster.py --dry-run       -> solo muestra, no publica
    python facebook_poster.py --limite 5      -> publica máximo 5
"""
import os
import json
import time
import argparse
import requests
from datetime import date, datetime
from empleo_utils import asegurar_id, nombre_archivo_oferta
from consola import configurar_salida_utf8

configurar_salida_utf8()

EMPLEOS_JSON = "empleos.json"
PUBLICADOS_JSON = "publicados_facebook.json"
GRAPH_API_VERSION = "v25.0"
FUENTE_URL = "https://app.servir.gob.pe/DifusionOfertasExterno/faces/consultas/ofertas_laborales.xhtml"
SITIO_URL = os.environ.get("SITIO_URL", "https://convocatoriasperutrabajo.github.io").rstrip("/")


def cargar_configuracion():
    if os.path.exists(".env"):
        with open(".env", "r", encoding="utf-8") as f:
            for linea in f:
                linea = linea.strip()
                if linea and not linea.startswith("#") and "=" in linea:
                    clave, valor = linea.split("=", 1)
                    os.environ.setdefault(clave.strip(), valor.strip())

    page_id = os.environ.get("FB_PAGE_ID")
    token = os.environ.get("FB_PAGE_ACCESS_TOKEN")
    if not page_id or not token:
        raise RuntimeError("Faltan FB_PAGE_ID y/o FB_PAGE_ACCESS_TOKEN (variables de entorno o .env).")
    return page_id, token


def cargar_json(ruta, valor_por_defecto):
    if os.path.exists(ruta):
        with open(ruta, "r", encoding="utf-8") as f:
            return json.load(f)
    return valor_por_defecto


def guardar_json(ruta, datos):
    with open(ruta, "w", encoding="utf-8", newline="\n") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)


def mostrar_remuneracion(valor: str) -> str:
    valor = str(valor or "").strip()
    return valor if valor.upper().startswith("S/.") else f"S/. {valor}"


def fecha_de_texto(valor: str):
    try:
        return datetime.strptime(str(valor or ""), "%d/%m/%Y").date()
    except ValueError:
        return None


def sigue_vigente(oferta: dict) -> bool:
    fecha_fin = fecha_de_texto(oferta.get("fecha_fin", ""))
    return fecha_fin is None or fecha_fin >= date.today()


def formatear_mensaje(oferta: dict) -> str:
    remuneracion = mostrar_remuneracion(oferta["remuneracion"])
    ficha_url = f"{SITIO_URL}/ofertas/{nombre_archivo_oferta(oferta)}"
    enlace_postulacion = oferta.get("url_postulacion")
    llamada_a_la_accion = (
        f"Postula directamente en el enlace oficial:\n{enlace_postulacion}\n\n"
        f"Requisitos, bases y resumen:\n{ficha_url}"
        if enlace_postulacion else
        f"Requisitos y enlace de postulación:\n{ficha_url}"
    )
    return (
        f"📢 NUEVA CONVOCATORIA\n\n"
        f"🔹 {oferta['titulo']}\n"
        f"🏢 {oferta['entidad']}\n"
        f"📍 {oferta['ubicacion']}\n"
        f"💰 Remuneración: {remuneracion}\n"
        f"👥 Vacantes: {oferta['vacantes']}\n"
        f"📅 Publicación: {oferta['fecha_inicio']} — Cierre: {oferta['fecha_fin']}\n\n"
        f"{llamada_a_la_accion}\n\n"
        f"#TrabajoPeru #Convocatoria #EmpleoPublico"
    )


def publicar_en_facebook(page_id: str, token: str, mensaje: str) -> dict:
    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{page_id}/feed"
    resp = requests.post(url, data={"message": mensaje, "access_token": token}, timeout=30)
    data = resp.json()
    if resp.status_code != 200 or "error" in data:
        raise RuntimeError(f"Error de la API de Facebook: {data}")
    return data


def ejecutar_publicador(limite: int = 20, dry_run: bool = False, pausa_segundos: float = 20):
    empleos = cargar_json(EMPLEOS_JSON, [])
    publicados = set(cargar_json(PUBLICADOS_JSON, []))

    # Compatibilidad: versiones anteriores guardaban solo el número de
    # convocatoria. Se respeta ese registro para no republicar al migrar.
    pendientes = sorted(
        (
            asegurar_id(o) for o in empleos
            if asegurar_id(o)["id"] not in publicados
            and o.get("numero_convocatoria") not in publicados
            and sigue_vigente(o)
        ),
        key=lambda oferta: fecha_de_texto(oferta.get("fecha_inicio", "")) or date.min,
        reverse=True,
    )[:limite]

    if not pendientes:
        print("No hay ofertas pendientes de publicar.")
        return

    print(f"{len(pendientes)} ofertas pendientes de publicar.\n")

    if dry_run:
        for o in pendientes:
            print("----- (dry-run, no se publica de verdad) -----")
            print(formatear_mensaje(o))
        return

    page_id, token = cargar_configuracion()

    errores = []
    for i, oferta in enumerate(pendientes, start=1):
        mensaje = formatear_mensaje(oferta)
        try:
            resultado = publicar_en_facebook(page_id, token, mensaje)
            publicados.add(oferta["id"])
            guardar_json(PUBLICADOS_JSON, sorted(publicados))  # guarda progreso tras cada post
            print(f"[{i}/{len(pendientes)}] ✅ Publicado: {oferta['titulo']} (post id: {resultado.get('id')})")
        except Exception as e:
            print(f"[{i}/{len(pendientes)}] ❌ Error publicando '{oferta['titulo']}': {e}")
            errores.append(oferta["id"])

        if i < len(pendientes):
            time.sleep(pausa_segundos)

    if errores:
        raise RuntimeError(f"Facebook rechazó {len(errores)} publicación(es)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Publica ofertas pendientes en la Página de Facebook")
    parser.add_argument("--limite", type=int, default=20)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--pausa", type=float, default=20)
    args = parser.parse_args()

    ejecutar_publicador(limite=args.limite, dry_run=args.dry_run, pausa_segundos=args.pausa)
