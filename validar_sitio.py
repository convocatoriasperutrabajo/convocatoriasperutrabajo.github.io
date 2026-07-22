"""Valida los datos y el sitio antes de que GitHub Actions publique cambios."""
import json
from pathlib import Path
from urllib.parse import urlparse

from consola import configurar_salida_utf8
from empleo_utils import asegurar_id, nombre_archivo_oferta


configurar_salida_utf8()

RAIZ = Path(__file__).resolve().parent
DOMINIOS_OFICIALES = ("gob.pe",)
CAMPOS_REQUERIDOS = (
    "titulo",
    "entidad",
    "ubicacion",
    "numero_convocatoria",
    "vacantes",
    "fecha_inicio",
    "fecha_fin",
    "url_oficial",
)


def es_url_oficial(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(host == dominio or host.endswith(f".{dominio}") for dominio in DOMINIOS_OFICIALES)


def validar() -> None:
    empleos = json.loads((RAIZ / "empleos.json").read_text(encoding="utf-8"))
    if not empleos:
        raise RuntimeError("empleos.json está vacío; se cancela la publicación")

    ids = set()
    esperadas = set()
    errores = []

    for posicion, original in enumerate(empleos, start=1):
        oferta = asegurar_id(original)
        faltantes = [campo for campo in CAMPOS_REQUERIDOS if not oferta.get(campo)]
        if faltantes:
            errores.append(f"oferta {posicion}: faltan {', '.join(faltantes)}")
        if oferta["id"] in ids:
            errores.append(f"oferta {posicion}: ID duplicado {oferta['id']}")
        ids.add(oferta["id"])

        url_oficial = str(oferta.get("url_oficial", ""))
        if url_oficial and not es_url_oficial(url_oficial):
            errores.append(f"oferta {posicion}: fuente no oficial {url_oficial}")

        archivo = nombre_archivo_oferta(oferta)
        esperadas.add(archivo)
        ficha = RAIZ / "ofertas" / archivo
        if not ficha.exists():
            errores.append(f"oferta {posicion}: no existe {ficha.relative_to(RAIZ)}")

        documento = oferta.get("archivo_oficial")
        if documento and not (RAIZ / documento).exists():
            errores.append(f"oferta {posicion}: no existe el documento {documento}")

    generadas = {p.name for p in (RAIZ / "ofertas").glob("*.html")}
    sobrantes = sorted(generadas - esperadas)
    if sobrantes:
        errores.append(f"hay páginas obsoletas: {', '.join(sobrantes[:5])}")

    if errores:
        raise RuntimeError("Sitio inválido:\n- " + "\n- ".join(errores))

    print(f"✅ Sitio validado: {len(empleos)} ofertas de fuente oficial")


if __name__ == "__main__":
    validar()
