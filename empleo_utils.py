"""Funciones compartidas para identificar convocatorias sin duplicarlas."""
import hashlib
import re
import unicodedata


FUENTE_OFICIAL = "SERVIR - Talento PerÃº"
URL_OFICIAL_SERVIR = "https://app.servir.gob.pe/DifusionOfertasExterno/faces/consultas/ofertas_laborales.xhtml"


def texto_clave(valor: object) -> str:
    """Normaliza texto para comparaciones, sin modificar lo que se muestra."""
    texto = unicodedata.normalize("NFKD", str(valor or ""))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", texto).strip().casefold()


def id_oferta(oferta: dict) -> str:
    """ID estable aun cuando dos entidades reutilicen el mismo nÃºmero."""
    partes = (
        texto_clave(oferta.get("entidad")),
        texto_clave(oferta.get("numero_convocatoria")),
        texto_clave(oferta.get("titulo")),
        texto_clave(oferta.get("ubicacion")),
    )
    return hashlib.sha256("|".join(partes).encode("utf-8")).hexdigest()[:20]


def asegurar_id(oferta: dict) -> dict:
    oferta = dict(oferta)
    oferta["id"] = id_oferta(oferta)
    oferta.setdefault("fuente", FUENTE_OFICIAL)
    oferta.setdefault("url_oficial", URL_OFICIAL_SERVIR)
    return oferta


def slugificar(valor: object, limite: int = 80) -> str:
    """Convierte texto en una parte de URL estable y legible."""
    texto = texto_clave(valor)
    texto = re.sub(r"[^a-z0-9]+", "-", texto).strip("-")
    return (texto[:limite] or "oferta").rstrip("-")


def nombre_archivo_oferta(oferta: dict) -> str:
    """Nombre Ãºnico de la ficha publicada en el sitio."""
    oferta = asegurar_id(oferta)
    base = f"{oferta['id']}-{oferta.get('titulo', '')}"
    return f"{slugificar(base)}.html"
