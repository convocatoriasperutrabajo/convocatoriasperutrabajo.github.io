"""Valida los datos y el sitio antes de que GitHub Actions publique cambios."""
import json
from pathlib import Path
from urllib.parse import urlparse

from consola import configurar_salida_utf8
from empleo_utils import asegurar_id, es_enlace_postulacion_directo, nombre_archivo_oferta


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


def es_url_postulacion_valida(url: str) -> bool:
    partes = urlparse(url)
    host = (partes.hostname or "").lower()
    bloqueados = (
        "convocatoriasdetrabajo.com",
        "perutrabajos.com",
        "empleosperu.gob.pe.fake",
    )
    return partes.scheme in {"http", "https"} and bool(host) and not any(
        host == dominio or host.endswith(f".{dominio}") for dominio in bloqueados
    )


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
        es_computrabajo = str(oferta.get("fuente", "")).casefold() == "computrabajo perú".casefold()
        es_indeed = str(oferta.get("fuente", "")).casefold() == "indeed perú".casefold()
        es_linkedin = str(oferta.get("fuente", "")).casefold() == "linkedin"
        host_oficial = (urlparse(url_oficial).hostname or "").lower()
        if es_computrabajo:
            if host_oficial != "pe.computrabajo.com" or "/ofertas-de-trabajo/" not in urlparse(url_oficial).path:
                errores.append(f"oferta {posicion}: aviso de Computrabajo no individual {url_oficial}")
        elif es_indeed:
            partes_indeed = urlparse(url_oficial)
            if host_oficial != "pe.indeed.com" or partes_indeed.path != "/viewjob" or "jk=" not in partes_indeed.query:
                errores.append(f"oferta {posicion}: aviso de Indeed no individual {url_oficial}")
        elif es_linkedin:
            if host_oficial != "pe.linkedin.com" or not urlparse(url_oficial).path.startswith("/jobs/view/"):
                errores.append(f"oferta {posicion}: aviso de LinkedIn no individual {url_oficial}")
        elif url_oficial and not es_url_oficial(url_oficial):
            errores.append(f"oferta {posicion}: fuente no oficial {url_oficial}")

        url_postulacion = str(oferta.get("url_postulacion", ""))
        if url_postulacion and (
            not es_url_postulacion_valida(url_postulacion)
            or not es_enlace_postulacion_directo(url_postulacion)
        ):
            errores.append(f"oferta {posicion}: el enlace no abre una postulación específica {url_postulacion}")

        url_consulta = str(oferta.get("url_consulta", ""))
        if url_consulta and not es_url_postulacion_valida(url_consulta):
            errores.append(f"oferta {posicion}: enlace de consulta inválido {url_consulta}")

        enlaces_bases = oferta.get("enlaces_bases", [])
        if enlaces_bases and not isinstance(enlaces_bases, list):
            errores.append(f"oferta {posicion}: enlaces_bases debe ser una lista")
        for enlace in enlaces_bases if isinstance(enlaces_bases, list) else []:
            url_base = str(enlace.get("url", "")) if isinstance(enlace, dict) else ""
            if not url_base or not es_url_postulacion_valida(url_base):
                errores.append(f"oferta {posicion}: enlace de bases inválido {url_base}")

        archivo = nombre_archivo_oferta(oferta)
        esperadas.add(archivo)
        ficha = RAIZ / "ofertas" / archivo
        if not ficha.exists():
            errores.append(f"oferta {posicion}: no existe {ficha.relative_to(RAIZ)}")
        else:
            contenido_ficha = ficha.read_text(encoding="utf-8")
            if "../documentos_oficiales/" in contenido_ficha or "Talento Perú (Word)" in contenido_ficha:
                errores.append(f"oferta {posicion}: la ficha todavía publica un aviso Word sin información útil")
            if 'class="btn-fuente"' in contenido_ficha or "Ver esta convocatoria en SERVIR" in contenido_ficha:
                errores.append(f"oferta {posicion}: la ficha envía al listado general de SERVIR")

        documento = oferta.get("archivo_oficial")
        if documento and not (RAIZ / documento).exists():
            errores.append(f"oferta {posicion}: no existe el documento {documento}")

    generadas = {p.name for p in (RAIZ / "ofertas").glob("*.html")}
    sobrantes = sorted(generadas - esperadas)
    if sobrantes:
        errores.append(f"hay páginas obsoletas: {', '.join(sobrantes[:5])}")

    if errores:
        raise RuntimeError("Sitio inválido:\n- " + "\n- ".join(errores))

    print(f"✅ Sitio validado: {len(empleos)} ofertas con enlaces verificados")


if __name__ == "__main__":
    validar()
