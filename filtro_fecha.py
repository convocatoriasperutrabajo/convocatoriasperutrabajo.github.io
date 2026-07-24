"""Interpreta textos de antigüedad publicados por las bolsas de empleo."""

import re
import unicodedata


def _normalizar(texto: object) -> str:
    valor = unicodedata.normalize("NFKD", str(texto or ""))
    valor = "".join(c for c in valor if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", valor).strip().casefold()


def dias_desde_publicacion(texto: object) -> int | None:
    """Convierte una antigüedad textual en días si se puede verificar."""
    valor = _normalizar(texto)
    if not valor or "mas de" in valor:
        return None
    if any(palabra in valor for palabra in ("hoy", "minuto", "hora", "recien")):
        return 0
    if "ayer" in valor:
        return 1
    coincidencia = re.search(r"hace\s+(\d+)\s+dias?", valor)
    if coincidencia:
        return int(coincidencia.group(1))
    coincidencia = re.search(r"hace\s+(\d+)\s+semanas?", valor)
    if coincidencia:
        return int(coincidencia.group(1)) * 7
    if any(palabra in valor for palabra in ("mes", "ano", "30+")):
        return None
    return None


def es_publicacion_reciente(texto: object, max_dias: int = 7) -> bool:
    """Acepta solamente antigüedades explícitas de hasta ``max_dias``."""
    dias = dias_desde_publicacion(texto)
    return dias is not None and dias <= max_dias
