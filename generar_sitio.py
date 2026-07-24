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
from config_canete import DISTRITOS_CANETE
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
    if not valor or valor.casefold() == "no especificado":
        return "No especificado"
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
      <h1><a href="{ruta_css}index.html">Empleos en Cañete</a></h1>
      <p class="masthead-sub">Ofertas de los 16 distritos de Cañete · enlaces directos al aviso original</p>
    </div>
  </div>
</header>
"""

PIE = """
<footer class="colophon">
  <p>Sitio independiente de difusión. Verifica siempre la vigencia y las condiciones en la página original antes de postular.</p>
</footer>
</body>
</html>
""".format(fuente=FUENTE_URL)


def generar_pagina_detalle(oferta: dict) -> str:
    remuneracion = mostrar_remuneracion(oferta.get("remuneracion", ""))
    url_postulacion = oferta.get("url_postulacion", "")
    url_consulta = oferta.get("url_consulta", "")
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
        'target="_blank" rel="noopener noreferrer">Ver oferta y postular →</a>'
        if url_postulacion else ""
    )
    aviso_enlace = (
        'El botón rojo abre la web oficial de la institución para que realices tu postulación.'
        if url_postulacion else (
        'La institución no publicó una dirección exacta para esta oferta. El botón gris abre su sección oficial de convocatorias. '
        'Busca allí el título y el número indicados en esta ficha.'
        if url_consulta else
        'La institución todavía no publicó un enlace directo para esta oferta. '
        'Revisa aquí los requisitos y el número de convocatoria.'
        )
    )
    accion_postulacion = (
        f'<div class="acciones-oficiales">{boton_postulacion}</div>'
        if boton_postulacion else (
        f'<div class="acciones-oficiales"><a class="btn-consulta" href="{html.escape(url_consulta, quote=True)}" '
        'target="_blank" rel="noopener noreferrer">Buscar en el portal de la institución →</a></div>'
        if url_consulta else
        '<p class="sin-enlace-directo">Aún no hay un enlace directo de postulación publicado por la institución; '
        'no te enviaremos a un listado general.</p>'
        )
    )
    aviso_certificado = (
        '<aside class="aviso-certificado" role="note"><strong>Aviso del portal DIRESA Madre de Dios</strong>'
        '<p>Su web oficial presenta un problema de certificado y el navegador puede mostrar una advertencia. '
        'Comprueba que la dirección sea <code>apps.diresamdd.gob.pe</code> antes de continuar. '
        'No ingreses contraseñas ni datos bancarios.</p></aside>'
        if "share.google/IovzweaQemtlVGF9i" in url_consulta else ""
    )
    ultimo_paso = (
        'Presiona el botón rojo para continuar en la web oficial de la institución.'
        if url_postulacion else (
        f'Abre el portal oficial y busca “{html.escape(oferta["titulo"])}” o el código SERVIR N° {html.escape(str(oferta.get("codigo_servir", "")))}.'
        if url_consulta else
        'Conserva el número de convocatoria y revisa los canales oficiales de la institución.'
        )
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
        '<p>Revisa todos los requisitos y condiciones en el aviso original antes de postular.</p></section>'
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
    {aviso_certificado}
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
        <div><dt>Referencia</dt><dd class="mono">{html.escape(oferta['numero_convocatoria'])}</dd></div>
        <div><dt>Fuente</dt><dd>{html.escape(str(oferta.get("fuente", "Aviso original")))}</dd></div>
        {f'<div><dt>Código SERVIR</dt><dd class="mono">N° {html.escape(str(oferta["codigo_servir"]))}</dd></div>' if oferta.get('codigo_servir') else ''}
        <div><dt>{"Fecha de publicación" if oferta.get("fuente") in {"Computrabajo Perú", "Indeed Perú", "LinkedIn", "Bumeran Perú"} else "Vigencia"}</dt><dd>{html.escape(oferta['fecha_inicio']) if oferta.get("fuente") in {"Computrabajo Perú", "Indeed Perú", "LinkedIn", "Bumeran Perú"} else f"{html.escape(oferta['fecha_inicio'])} — {html.escape(oferta['fecha_fin'])}"}</dd></div>
      </dl>
      <div class="guia-postulacion">
        <strong>Antes de postular</strong>
        <span class="numero-destacado">Referencia: {html.escape(oferta['numero_convocatoria'])}</span>
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
    por_distrito = {}
    for original in empleos:
        o = asegurar_id(original)
        depto, provincia, distrito = ubicacion_desglosada(o)
        nombre_distrito = distrito or provincia or depto
        por_distrito.setdefault(nombre_distrito, []).append(o)

    secciones_html = []
    for nombre_distrito in DISTRITOS_CANETE:
        items = []
        ofertas_distrito = por_distrito.get(nombre_distrito, [])
        for o in sorted(ofertas_distrito, key=lambda x: x["titulo"]):
            archivo = nombre_archivo_oferta(o)
            depto, provincia, distrito = ubicacion_desglosada(o)
            codigo = f" · SERVIR N° {html.escape(str(o['codigo_servir']))}" if o.get("codigo_servir") else ""
            perfil = str(o.get("formacion_academica", "")).strip()
            perfil_html = f'<span class="job-profile">{html.escape(perfil)}</span>' if perfil else ""
            items.append(f"""
                <li class="job-item" data-id="{html.escape(o['id'], quote=True)}" data-titulo="{html.escape(o['titulo'], quote=True)}" data-entidad="{html.escape(o['entidad'], quote=True)}" data-departamento="{html.escape(depto, quote=True)}" data-provincia="{html.escape(provincia, quote=True)}" data-distrito="{html.escape(distrito, quote=True)}">
                    <a href="ofertas/{archivo}" class="job-link">
                        <span class="job-title">{html.escape(o['titulo'])}</span>
                        <span class="job-meta">{html.escape(o['entidad'])} · {html.escape(o['vacantes'])} vacante(s){codigo} <span class="source-badge">{html.escape(str(o.get("fuente", "Fuente original")))}</span></span>
                        {perfil_html}
                    </a>
                    <button type="button" class="favorite-toggle" aria-label="Guardar {html.escape(o['titulo'], quote=True)}" aria-pressed="false" title="Guardar oferta">☆</button>
                </li>""")
        secciones_html.append(f"""
        <section class="dep-section" data-seccion-distrito="{html.escape(nombre_distrito, quote=True)}">
            <h2>
              <button type="button" class="district-heading" aria-expanded="true">
                <span>📍 {html.escape(nombre_distrito)}</span>
                <span class="district-count">{len(ofertas_distrito)} ofertas <span class="toggle-icon" aria-hidden="true">−</span></span>
              </button>
            </h2>
            <ul class="job-list">{''.join(items) if items else '<li class="district-empty">Todavía no encontramos ofertas en este distrito.</li>'}</ul>
        </section>""")

    accesos_distritos = "".join(
        f'<button type="button" class="district-chip" data-distrito="{html.escape(nombre, quote=True)}">'
        f'{html.escape(nombre.title())}<span>{len(por_distrito.get(nombre, []))}</span></button>'
        for nombre in DISTRITOS_CANETE
    )

    contenido = CABECERA.format(
        titulo="Empleos en Cañete — ofertas en sus 16 distritos",
        descripcion="Ofertas laborales de toda la provincia de Cañete, organizadas por distrito y con enlace al aviso original.",
        ruta_css="",
    ) + f"""
<main class="layout-index">
  <section class="buscador-ubicacion" aria-labelledby="titulo-buscador">
    <h2 id="titulo-buscador">Encuentra empleo cerca de ti</h2>
    <p>Busca por puesto o empresa y elige tu distrito.</p>
    <div class="search-row">
      <div class="filtro-control search-control">
        <label for="buscar-ofertas">Buscar empleo</label>
        <input type="search" id="buscar-ofertas" placeholder="Ejemplo: operario, ventas, banco…" autocomplete="off">
      </div>
      <div class="filtro-control sort-control">
        <label for="orden-ofertas">Ordenar resultados</label>
        <select id="orden-ofertas">
          <option value="titulo">Puesto: A–Z</option>
          <option value="empresa">Empresa: A–Z</option>
        </select>
      </div>
    </div>
    <div class="district-chips" aria-label="Accesos rápidos por distrito">
      <button type="button" class="district-chip active" data-distrito="">Todos <span>{len(empleos)}</span></button>
      {accesos_distritos}
    </div>
    <div class="controles-ubicacion">
      <div class="filtro-control filtro-fijo"><label for="departamento-fijo">Departamento</label><input id="departamento-fijo" type="text" value="Lima" readonly aria-readonly="true"></div>
      <div class="filtro-control filtro-fijo"><label for="provincia-fija">Provincia</label><input id="provincia-fija" type="text" value="Cañete" readonly aria-readonly="true"></div>
      <div class="filtro-control"><label for="filtro-distrito">Distrito</label><select id="filtro-distrito">{opciones_filtro(set(DISTRITOS_CANETE), 'Todos los distritos')}</select></div>
    </div>
    <div class="filter-actions">
      <button type="button" class="saved-filter" id="ver-guardados" aria-pressed="false">☆ Ver guardados <span id="cantidad-guardados">0</span></button>
      <button type="button" class="limpiar-filtros" id="limpiar-filtros">Limpiar búsqueda</button>
    </div>
  </section>
  <p class="total-ofertas" id="contador-resultados" aria-live="polite">{len(empleos)} ofertas registradas actualmente.</p>
  {''.join(secciones_html) if secciones_html else '<p class="empty-state">Todavía no hay ofertas cargadas. Corre scraper.py primero.</p>'}
  <p class="empty-state resultados-vacios" id="resultados-vacios" hidden>No encontramos ofertas para ese distrito. Prueba con otro distrito o mira todas las ofertas.</p>
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
