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
from empleo_utils import asegurar_id
from consola import configurar_salida_utf8

configurar_salida_utf8()

EMPLEOS_JSON = "empleos.json"
CARPETA_OFERTAS = "ofertas"

FUENTE_URL = "https://app.servir.gob.pe/DifusionOfertasExterno/faces/consultas/ofertas_laborales.xhtml"


def slugify(texto: str) -> str:
    texto = texto.lower()
    texto = re.sub(r'[^a-z0-9]+', '-', texto).strip('-')
    return texto[:80] if texto else "oferta"


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
    return CABECERA.format(
        titulo=html.escape(f"{oferta['titulo']} — {oferta['entidad']}"),
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
        <div><dt>Ubicación</dt><dd>{html.escape(oferta['ubicacion'])}</dd></div>
        <div><dt>Remuneración</dt><dd>{html.escape(remuneracion)}</dd></div>
        <div><dt>Número de convocatoria</dt><dd class="mono">{html.escape(oferta['numero_convocatoria'])}</dd></div>
        <div><dt>Vigencia</dt><dd>{html.escape(oferta['fecha_inicio'])} — {html.escape(oferta['fecha_fin'])}</dd></div>
      </dl>
      <a class="btn-oficial" href="{FUENTE_URL}" target="_blank" rel="noopener">Ver y postular en el portal oficial de SERVIR →</a>
    </div>
  </article>
</main>
""" + PIE


def generar_index(empleos: list) -> str:
    por_departamento = {}
    for original in empleos:
        o = asegurar_id(original)
        depto = o.get("departamento") or "Sin región especificada"
        por_departamento.setdefault(depto, []).append(o)

    secciones_html = []
    for depto in sorted(por_departamento.keys()):
        items = []
        for o in sorted(por_departamento[depto], key=lambda x: x["titulo"]):
            slug = slugify(f"{o['id']}-{o['titulo']}")
            items.append(f"""
                <li>
                    <a href="ofertas/{slug}.html" class="job-link">
                        <span class="job-title">{html.escape(o['titulo'])}</span>
                        <span class="job-meta">{html.escape(o['entidad'])} · {html.escape(o['vacantes'])} vacante(s)</span>
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
  <p class="total-ofertas">{len(empleos)} ofertas registradas actualmente.</p>
  {''.join(secciones_html) if secciones_html else '<p class="empty-state">Todavía no hay ofertas cargadas. Corre scraper.py primero.</p>'}
</main>
""" + PIE

    return contenido


def ejecutar():
    empleos = cargar_empleos()
    os.makedirs(CARPETA_OFERTAS, exist_ok=True)

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(generar_index(empleos))
    print(f"✅ index.html generado con {len(empleos)} ofertas")

    for original in empleos:
        o = asegurar_id(original)
        slug = slugify(f"{o['id']}-{o['titulo']}")
        ruta = os.path.join(CARPETA_OFERTAS, f"{slug}.html")
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(generar_pagina_detalle(o))

    print(f"✅ {len(empleos)} páginas de detalle generadas en /{CARPETA_OFERTAS}/")


if __name__ == "__main__":
    ejecutar()
