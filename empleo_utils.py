"""Funciones compartidas para identificar convocatorias sin duplicarlas."""
import hashlib
import re
import unicodedata


def texto_clave(valor: object) -> str:
    """Normaliza texto para comparaciones, sin modificar lo que se muestra."""
    texto = unicodedata.normalize("NFKD", str(valor or ""))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", texto).strip().casefold()


def id_oferta(oferta: dict) -> str:
    """ID estable aun cuando dos entidades reutilicen el mismo número."""
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
    return oferta
