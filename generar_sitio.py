"""
generar_sitio.py
Lee empleos.json y genera:
  - index.html (listado agrupado por región)
  - ofertas/<slug>.html (una página de detalle por cada oferta)

Uso:
    python generar_sitio.py
"""
import os
import json
import re
import html
from empleo_utils import asegurar_id, nombre_archivo_oferta
from consola import configurar_salida_utf8

configurar_salida_utf8()

EMPLEOS_JSON = "empleos.json"
CARPETA_OFERTAS = "ofertas"

FUENTE_URL = "https://app.servir.gob.pe/DifusionOfertasExterno/faces/consultas/ofertas_laborales.xhtml"


def cargar_empleos():
    if not os.path.exists(EMPLEOS_JSON):
        return []
    with open(EMPLEOS_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def mostrar_remuneracion(valor: str) -> str:
    valor = str(valor or "").strip()
    return valor if valor.upper().startswith("S/.") else f"S/. {valor}"


def limpiar_html(contenido: str) -> str:
    """Evita espacios residuales cuando un bloque opcional queda vacío."""
    return re.sub(r"[ \t]+(?=\n)", "", contenido)


CABECERA = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{titulo}</title>
<meta name="description" content="{descripcion}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600;9..144,700&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{ruta_css}static/style.css">
<script defer src="{ruta_css}static/filtros.js"></script>
</head>
<body>
<header class="masthead">
  <div class="masthead-inner">
    <a href="{ruta_css}index.html" class="masthead-mark-link"><span class="masthead-mark">☰</span></a>
    <div class="masthead-text">
      <h1><a href="{ruta_css}index.html">Bolsa de Empleo Público — Perú</a></h1>
      <p class="masthead-sub">Recopilado automáticamente del portal oficial de SERVIR (Talento Perú) · no es un sitio del Estado</p>
    </div>
  </div>
</header>
"""

PIE = """
<footer class="colophon">
  <p>Los datos de esta página provienen del <a href="{fuente}" target="_blank" rel="noopener">portal oficial de SERVIR — Talento Perú</a>.
  Este es un sitio de difusión independiente y no oficial; verifica siempre los detalles y postula directamente en el portal del Estado.</p>
</footer>
</body>
</html>
""".format(fuente=FUENTE_URL)


def generar_pagina_detalle(oferta: dict) -> str:
    remuneracion = mostrar_remuneracion(oferta.get("remuneracion", ""))
    url_postulacion = oferta.get("url_postulacion", "")
    documentos = []
    for enlace in oferta.get("enlaces_bases", []):
        if not isinstance(enlace, dict) or not enlace.get("url"):
            continue
        titulo = str(enlace.get("titulo") or "Descargar bases o anexo oficial")
        documentos.append(
            f'<li><a href="{html.escape(str(enlace["url"]), quote=True)}" target="_blank" '
            f'rel="noopener noreferrer">{html.escape(titulo)} ↗</a></li>'
        )
    boton_postulacion = (
        f'<a class="btn-oficial" href="{html.escape(url_postulacion, quote=True)}" '
        'target="_blank" rel="noopener noreferrer">Postular en la institución →</a>'
        if url_postulacion else ""
    )
    aviso_enlace = (
        'El botón rojo abre la web oficial de la institución para que realices tu postulación.'
        if url_postulacion else
        'La institución todavía no publicó un enlace directo para esta oferta. '
        'Revisa aquí los requisitos y el número de convocatoria; no te enviaremos a un listado general.'
    )
    accion_postulacion = (
        f'<div class="acciones-oficiales">{boton_postulacion}</div>'
        if boton_postulacion else
        '<p class="sin-enlace-directo">Aún no hay un enlace directo de postulación publicado por la institución.</p>'
    )
    ultimo_paso = (
        'Presiona el botón rojo para continuar en la web oficial de la institución.'
        if url_postulacion else
        'Conserva el número de convocatoria y revisa los canales oficiales de la institución.'
    )
    etiquetas = (
        ("Requerimiento", "requerimiento"),
        ("Experiencia", "experiencia"),
        ("Formación académica", "formacion_academica"),
        ("Especialización", "especializacion"),
        ("Conocimientos", "conocimiento"),
        ("Competencias", "competencias"),
        ("Detalle publicado por la entidad", "detalle_entidad"),
    )
    requisitos = "".join(
        f'<div class="requisito"><h3>{etiqueta}</h3><p>{html.escape(str(oferta[campo]))}</p></div>'
        for etiqueta, campo in etiquetas if oferta.get(campo)
    )
    requisitos_html = (
        f'<section class="requisitos" id="requisitos"><h2>Requisitos que debes cumplir</h2>{requisitos}</section>'
        if requisitos else
        '<section class="requisitos" id="requisitos"><h2>Requisitos que debes cumplir</h2>'
        '<p>La ficha oficial todavía no muestra el detalle de requisitos. Revisa las bases o la página de la institución antes de postular.</p></section>'
    )
    documentos_html = (
        '<section class="documentos" id="documentos"><h2>Bases, anexos y documentos oficiales</h2>'
        f'<ul class="lista-documentos">{"".join(documentos)}</ul></section>'
        if documentos else
        '<section class="documentos" id="documentos"><h2>Bases, anexos y documentos oficiales</h2>'
        '<p>La fuente oficial no entregó un archivo de bases para esta oferta. Revisa los canales oficiales de la institución antes de postular.</p></section>'
    )
    pasos_html = f"""
  <section class="pasos-postulacion" id="como-postular">
    <h2>Cómo postular</h2>
    <ol>
      <li>Lee los requisitos y revisa los documentos oficiales de esta página.</li>
      <li>Ten listos tu DNI, CV y anexos que la entidad solicite.</li>
      <li>{ultimo_paso}</li>
    </ol>
    <p>No necesitas crear una cuenta en esta página para revisar la convocatoria.</p>
    {accion_postulacion}
  </section>"""
    return CABECERA.format(
        titulo=html.escape(f"{oferta['titulo']} — {oferta['entidad']}"),
        descripcion=html.escape(f"{oferta['titulo']} en {oferta['ubicacion']}. {oferta['vacantes']} vacante(s)."),
        ruta_css="../",
    ) + f"""
<main class="detalle">
  <nav class="navegacion-ficha" aria-label="Contenido de la convocatoria">
    <a href="#requisitos">Requisitos</a>
    <a href="#documentos">Bases y anexos</a>
    <a href="#como-postular">Cómo postular</a>
  </nav>
  <article class="notice notice-detalle">
    <div class="notice-seal">
      <span class="seal-number">{html.escape(oferta['vacantes'])}</span>
      <span class="seal-label">vacante{'s' if oferta['vacantes'] != '1' else ''}</span>
    </div>
    <div class="notice-body">
      <h2 class="notice-title">{html.escape(oferta['titulo'])}</h2>
      <p class="notice-entity">{html.escape(oferta['entidad'])}</p>
      <dl class="notice-facts">
        <div><dt>Ubicación</dt><dd>{html.escape(oferta['ubicacion'])}</dd></div>
        <div><dt>Remuneración</dt><dd>{html.escape(remuneracion)}</dd></div>
        <div><dt>Número de convocatoria</dt><dd class="mono">{html.escape(oferta['numero_convocatoria'])}</dd></div>
        {f'<div><dt>Código SERVIR</dt><dd class="mono">N° {html.escape(str(oferta["codigo_servir"]))}</dd></div>' if oferta.get('codigo_servir') else ''}
        <div><dt>Vigencia</dt><dd>{html.escape(oferta['fecha_inicio'])} — {html.escape(oferta['fecha_fin'])}</dd></div>
      </dl>
      <div class="guia-postulacion">
        <strong>Antes de postular</strong>
        <span class="numero-destacado">Convocatoria: {html.escape(oferta['numero_convocatoria'])}</span>
        {f'<span class="codigo-servir">Código SERVIR: N° {html.escape(str(oferta["codigo_servir"]))}</span>' if oferta.get('codigo_servir') else ''}
        <p>{aviso_enlace}</p>
      </div>
    </div>
  </article>
  {requisitos_html}
  {documentos_html}
  {pasos_html}
</main>
""" + PIE


def ubicacion_desglosada(oferta: dict) -> tuple[str, str, str]:
    """Obtiene departamento, provincia/localidad y distrito si la fuente lo informa."""
    partes = [parte.strip() for parte in str(oferta.get("ubicacion", "")).split("-") if parte.strip()]
    departamento = str(oferta.get("departamento") or (partes[0] if partes else "Sin región especificada"))
    provincia = str(oferta.get("provincia") or (partes[1] if len(partes) > 1 else ""))
    distrito = str(oferta.get("distrito") or (partes[2] if len(partes) > 2 else ""))
    return departamento, provincia, distrito


def opciones_filtro(valores: set[str], etiqueta: str) -> str:
    opciones = [f'<option value="">{etiqueta}</option>']
    opciones.extend(
        f'<option value="{html.escape(valor, quote=True)}">{html.escape(valor)}</option>'
        for valor in sorted(valor for valor in valores if valor)
    )
    return "".join(opciones)


def generar_index(empleos: list) -> str:
    por_departamento = {}
    departamentos, provincias, distritos = set(), set(), set()
    for original in empleos:
        o = asegurar_id(original)
        depto, provincia, distrito = ubicacion_desglosada(o)
        por_departamento.setdefault(depto, []).append(o)
        departamentos.add(depto)
        provincias.add(provincia)
        distritos.add(distrito)

    secciones_html = []
    for depto in sorted(por_departamento.keys()):
        items = []
        for o in sorted(por_departamento[depto], key=lambda x: x["titulo"]):
            archivo = nombre_archivo_oferta(o)
            _, provincia, distrito = ubicacion_desglosada(o)
            codigo = f" · SERVIR N° {html.escape(str(o['codigo_servir']))}" if o.get("codigo_servir") else ""
            perfil = str(o.get("formacion_academica", "")).strip()
            perfil_html = f'<span class="job-profile">{html.escape(perfil)}</span>' if perfil else ""
            items.append(f"""
                <li class="job-item" data-departamento="{html.escape(depto, quote=True)}" data-provincia="{html.escape(provincia, quote=True)}" data-distrito="{html.escape(distrito, quote=True)}">
                    <a href="ofertas/{archivo}" class="job-link">
                        <span class="job-title">{html.escape(o['titulo'])}</span>
                        <span class="job-meta">{html.escape(o['entidad'])} · {html.escape(o['vacantes'])} vacante(s){codigo}</span>
                        {perfil_html}
                    </a>
                </li>""")
        secciones_html.append(f"""
        <section class="dep-section">
            <h2>📍 {html.escape(depto)}</h2>
            <ul class="job-list">{''.join(items)}</ul>
        </section>""")

    contenido = CABECERA.format(
        titulo="Bolsa de Empleo Público — Perú (fuente: SERVIR)",
        descripcion="Convocatorias laborales del sector público peruano, recopiladas automáticamente del portal oficial de SERVIR.",
        ruta_css="",
    ) + f"""
<main class="layout-index">
  <section class="buscador-ubicacion" aria-labelledby="titulo-buscador">
    <h2 id="titulo-buscador">Encuentra empleo cerca de ti</h2>
    <p>Elige tu ubicación. No necesitas saber el nombre de la entidad.</p>
    <div class="controles-ubicacion">
      <div class="filtro-control"><label for="filtro-departamento">Departamento</label><select id="filtro-departamento">{opciones_filtro(departamentos, 'Todo el Perú')}</select></div>
      <div class="filtro-control"><label for="filtro-provincia">Provincia o localidad</label><select id="filtro-provincia">{opciones_filtro(provincias, 'Todas las provincias')}</select></div>
      <div class="filtro-control"><label for="filtro-distrito">Distrito</label><select id="filtro-distrito">{opciones_filtro(distritos, 'Todos los distritos')}</select></div>
    </div>
    <button type="button" class="limpiar-filtros" id="limpiar-filtros">Ver todas las ofertas</button>
  </section>
  <p class="total-ofertas" id="contador-resultados" aria-live="polite">{len(empleos)} ofertas registradas actualmente.</p>
  {''.join(secciones_html) if secciones_html else '<p class="empty-state">Todavía no hay ofertas cargadas. Corre scraper.py primero.</p>'}
  <p class="empty-state resultados-vacios" id="resultados-vacios" hidden>No encontramos ofertas para esa ubicación. Prueba con otro departamento o mira todas las ofertas.</p>
</main>
""" + PIE

    return contenido


def ejecutar():
    empleos = cargar_empleos()
    os.makedirs(CARPETA_OFERTAS, exist_ok=True)

    with open("index.html", "w", encoding="utf-8", newline="\n") as f:
        f.write(limpiar_html(generar_index(empleos)))
    print(f"✅ index.html generado con {len(empleos)} ofertas")

    esperados = set()
    for original in empleos:
        o = asegurar_id(original)
        archivo = nombre_archivo_oferta(o)
        esperados.add(archivo)
        ruta = os.path.join(CARPETA_OFERTAS, archivo)
        with open(ruta, "w", encoding="utf-8", newline="\n") as f:
            f.write(limpiar_html(generar_pagina_detalle(o)))

    eliminadas = 0
    for archivo in os.listdir(CARPETA_OFERTAS):
        if archivo.endswith(".html") and archivo not in esperados:
            os.remove(os.path.join(CARPETA_OFERTAS, archivo))
            eliminadas += 1

    print(f"✅ {len(empleos)} páginas de detalle generadas en /{CARPETA_OFERTAS}/")
    if eliminadas:
        print(f"🧹 {eliminadas} páginas obsoletas eliminadas")


if __name__ == "__main__":
    ejecutar()
