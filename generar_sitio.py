"""
generar_sitio.py
Lee empleos.json y genera:
  - index.html (listado agrupado por regiÃ³n)
  - ofertas/<slug>.html (una pÃ¡gina de detalle por cada oferta)

Uso:
    python generar_sitio.py
"""
import os
import json
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
</head>
<body>
<header class="masthead">
  <div class="masthead-inner">
    <a href="{ruta_css}index.html" class="masthead-mark-link"><span class="masthead-mark">â˜°</span></a>
    <div class="masthead-text">
      <h1><a href="{ruta_css}index.html">Bolsa de Empleo PÃºblico â€” PerÃº</a></h1>
      <p class="masthead-sub">Recopilado automÃ¡ticamente del portal oficial de SERVIR (Talento PerÃº) Â· no es un sitio del Estado</p>
    </div>
  </div>
</header>
"""

PIE = """
<footer class="colophon">
  <p>Los datos de esta pÃ¡gina provienen del <a href="{fuente}" target="_blank" rel="noopener">portal oficial de SERVIR â€” Talento PerÃº</a>.
  Este es un sitio de difusiÃ³n independiente y no oficial; verifica siempre los detalles y postula directamente en el portal del Estado.</p>
</footer>
</body>
</html>
""".format(fuente=FUENTE_URL)


def generar_pagina_detalle(oferta: dict) -> str:
    remuneracion = mostrar_remuneracion(oferta.get("remuneracion", ""))
    archivo_oficial = oferta.get("archivo_oficial", "")
    url_oficial = oferta.get("url_oficial") or FUENTE_URL
    boton_documento = (
        f'<a class="btn-oficial" href="../{html.escape(archivo_oficial)}" target="_blank" rel="noopener">'
        'Abrir documento oficial de esta convocatoria â†’</a>'
        if archivo_oficial else ""
    )
    boton_fuente = (
        f'<a class="btn-fuente" href="{html.escape(url_oficial, quote=True)}" '
        'target="_blank" rel="noopener">Ir a la fuente oficial del Estado â†’</a>'
    )
    return CABECERA.format(
        titulo=html.escape(f"{oferta['titulo']} â€” {oferta['entidad']}"),
        descripcion=html.escape(f"{oferta['titulo']} en {oferta['ubicacion']}. {oferta['vacantes']} vacante(s)."),
        ruta_css="../",
    ) + f"""
<main class="detalle">
  <article class="notice notice-detalle">
    <div class="notice-seal">
      <span class="seal-number">{html.escape(oferta['vacantes'])}</span>
      <span class="seal-label">vacante{'s' if oferta['vacantes'] != '1' else ''}</span>
    </div>
    <div class="notice-body">
      <h2 class="notice-title">{html.escape(oferta['titulo'])}</h2>
      <p class="notice-entity">{html.escape(oferta['entidad'])}</p>
      <dl class="notice-facts">
        <div><dt>UbicaciÃ³n</dt><dd>{html.escape(oferta['ubicacion'])}</dd></div>
        <div><dt>RemuneraciÃ³n</dt><dd>{html.escape(remuneracion)}</dd></div>
        <div><dt>NÃºmero de convocatoria</dt><dd class="mono">{html.escape(oferta['numero_convocatoria'])}</dd></div>
        <div><dt>Vigencia</dt><dd>{html.escape(oferta['fecha_inicio'])} â€” {html.escape(oferta['fecha_fin'])}</dd></div>
      </dl>
      <p class="aviso-oficial">Verifica los requisitos y el cronograma antes de postular.</p>
      <div class="acciones-oficiales">{boton_documento}{boton_fuente}</div>
    </div>
  </article>
</main>
""" + PIE


def generar_index(empleos: list) -> str:
    por_departamento = {}
    for original in empleos:
        o = asegurar_id(original)
        depto = o.get("departamento") or "Sin regiÃ³n especificada"
        por_departamento.setdefault(depto, []).append(o)

    secciones_html = []
    for depto in sorted(por_departamento.keys()):
        items = []
        for o in sorted(por_departamento[depto], key=lambda x: x["titulo"]):
            archivo = nombre_archivo_oferta(o)
            items.append(f"""
                <li>
                    <a href="ofertas/{archivo}" class="job-link">
                        <span class="job-title">{html.escape(o['titulo'])}</span>
                        <span class="job-meta">{html.escape(o['entidad'])} Â· {html.escape(o['vacantes'])} vacante(s)</span>
                    </a>
                </li>""")
        secciones_html.append(f"""
        <section class="dep-section">
            <h2>ðŸ“ {html.escape(depto)}</h2>
            <ul class="job-list">{''.join(items)}</ul>
        </section>""")

    contenido = CABECERA.format(
        titulo="Bolsa de Empleo PÃºblico â€” PerÃº (fuente: SERVIR)",
        descripcion="Convocatorias laborales del sector pÃºblico peruano, recopiladas automÃ¡ticamente del portal oficial de SERVIR.",
        ruta_css="",
    ) + f"""
<main class="layout-index">
  <p class="total-ofertas">{len(empleos)} ofertas registradas actualmente.</p>
  {''.join(secciones_html) if secciones_html else '<p class="empty-state">TodavÃ­a no hay ofertas cargadas. Corre scraper.py primero.</p>'}
</main>
""" + PIE

    return contenido


def ejecutar():
    empleos = cargar_empleos()
    os.makedirs(CARPETA_OFERTAS, exist_ok=True)

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(generar_index(empleos))
    print(f"âœ… index.html generado con {len(empleos)} ofertas")

    esperados = set()
    for original in empleos:
        o = asegurar_id(original)
        archivo = nombre_archivo_oferta(o)
        esperados.add(archivo)
        ruta = os.path.join(CARPETA_OFERTAS, archivo)
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(generar_pagina_detalle(o))

    eliminadas = 0
    for archivo in os.listdir(CARPETA_OFERTAS):
        if archivo.endswith(".html") and archivo not in esperados:
            os.remove(os.path.join(CARPETA_OFERTAS, archivo))
            eliminadas += 1

    print(f"âœ… {len(empleos)} pÃ¡ginas de detalle generadas en /{CARPETA_OFERTAS}/")
    if eliminadas:
        print(f"ðŸ§¹ {eliminadas} pÃ¡ginas obsoletas eliminadas")


if __name__ == "__main__":
    ejecutar()
