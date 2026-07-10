import os
import json
import requests
from bs4 import BeautifulSoup

# ==========================================
# CONFIGURACIÓN DE TU PÁGINA DE FACEBOOK
# ==========================================
FB_PAGE_ID = "AQUÍ_VA_EL_ID_DE_TU_PÁGINA"
FB_ACCESS_TOKEN = "AQUÍ_VA_TU_TOKEN_DE_ACCESO"
# ==========================================

URL_ORIGEN = "https://www.convocatoriasdetrabajo.com/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
ARCHIVO_BD = "empleos.json"

def cargar_empleos_guardados():
    if os.path.exists(ARCHIVO_BD):
        with open(ARCHIVO_BD, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def guardar_empleos(empleos):
    with open(ARCHIVO_BD, "w", encoding="utf-8") as f:
        json.dump(empleos, f, ensure_ascii=False, indent=4)

def publicar_en_facebook(titulo, nombre_archivo_web, depar):
    enlace_mi_web = f"https://convocatoriasperutrabajo.github.io/{nombre_archivo_web}"
    mensaje = f"📢 ¡Nueva Convocatoria Estatal en {depar.upper()}! 💼\n\n📌 {titulo}\n\n👇 Revisa los requisitos oficiales y cómo postular aquí:"
    
    url_fb = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/feed"
    payload = {"message": mensaje, "link": enlace_mi_web, "access_token": FB_ACCESS_TOKEN}
    
    if "AQUÍ_VA_" in FB_ACCESS_TOKEN:
        print(f"   [SIMULACIÓN FACEBOOK] Post enviado -> {enlace_mi_web}")
        return
        
    try:
        respuesta = requests.post(url_fb, data=payload, timeout=10)
        if respuesta.status_code == 200:
            print("✅ ¡Publicado en Facebook!")
        else:
            print(f"❌ Error Facebook: {respuesta.text}")
    except Exception as e:
        print(f"💥 Conexión fallida Facebook: {e}")

def extraer_datos_geograficos(texto_bloque):
    dep = "Lima"
    prov = "Especificado en el enlace"
    dist = "Especificado en el enlace"
    
    texto_min = texto_bloque.lower()
    departamentos_peru = [
        "amazonas", "ancash", "apurimac", "arequipa", "ayacucho", "cajamarca", 
        "callao", "cusco", "huancavelica", "huanuco", "ica", "junin", 
        "la libertad", "lambayeque", "lima", "loreto", "madre de dios", 
        "moquegua", "pasco", "piura", "puno", "san martin", "tacna", "tumbes", "ucayali"
    ]
    
    for d in departamentos_peru:
        if d in texto_min:
            dep = d.capitalize()
            break
            
    return dep, prov, dist

def generar_portada_principal(empleos):
    """Genera automáticamente el archivo index.html organizando los empleos por departamento."""
    print("🏠 Actualizando la portada principal (index.html)...")
    
    # Agrupar los empleos por departamento
    empleos_por_dep = {}
    for emp in empleos:
        dep = emp.get("ubicacion", {}).get("departamento", "Lima")
        if dep not in empleos_por_dep:
            empleos_por_dep[dep] = []
        empleos_por_dep[dep].append(emp)
    
    # Construir el contenido dinámico de los departamentos y sus enlaces
    contenido_html = ""
    for dep, lista_empleos in sorted(empleos_por_dep.items()):
        contenido_html += f"""
        <div class="dep-section">
            <h2>📍 Región {dep}</h2>
            <ul class="job-list">"""
        
        # Mostrar los últimos empleos subidos de este departamento primero
        for emp in reversed(lista_empleos):
            contenido_html += f"""
                <li>
                    <a href="{emp['archivo_web']}" class="job-link">
                        <span class="job-title">{emp['titulo']}</span>
                    </a>
                </li>"""
        contenido_html += """
            </ul>
        </div>"""

    # Estructura completa de la página de inicio
    html_completo = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Convocatorias Perú Trabajo - Portal Oficial</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 0; padding: 0; background-color: #f4f6f9; color: #333; }}
        header {{ background-color: #0056b3; color: white; padding: 25px 20px; text-align: center; border-bottom: 4px solid #d91d1d; }}
        header h1 {{ margin: 0; font-size: 26px; }}
        header p {{ margin: 5px 0 0 0; font-size: 14px; opacity: 0.9; }}
        .container {{ max-width: 900px; margin: 30px auto; padding: 0 20px; }}
        .dep-section {{ background: white; margin-bottom: 25px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); padding: 20px; border-left: 5px solid #0056b3; }}
        .dep-section h2 {{ margin-top: 0; color: #0056b3; font-size: 18px; border-bottom: 1px solid #e2e8f0; padding-bottom: 8px; }}
        .job-list {{ list-style: none; padding: 0; margin: 10px 0 0 0; }}
        .job-list li {{ padding: 10px 0; border-bottom: 1px dashed #edf2f7; }}
        .job-list li:last-child {{ border-bottom: none; }}
        .job-link {{ text-decoration: none; color: #2d3748; display: block; font-size: 15px; transition: color 0.2s; }}
        .job-link:hover {{ color: #d91d1d; }}
        .job-title {{ font-weight: 500; }}
    </style>
</head>
<body>
    <header>
        <h1>Convocatorias de Trabajo del Estado</h1>
        <p>Busca de forma rápida y directa las plazas oficiales vigentes en tu región</p>
    </header>
    
    <div class="container">
        {contenido_html}
    </div>
</body>
</html>"""

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_completo)
    print("✅ Portada principal actualizada correctamente.")

def procesar_convocatorias():
    print("🔍 Conectando con la base de datos de convocatorias vigentes...")
    empleos_guardados = cargar_empleos_guardados()
    enlaces_existentes = [emp.get("enlace_origen") for emp in empleos_guardados]
    
    try:
        respuesta = requests.get(URL_ORIGEN, headers=HEADERS, timeout=15)
        if respuesta.status_code != 200:
            print(f"❌ Error al acceder a la fuente: {respuesta.status_code}")
            return
            
        soup = BeautifulSoup(respuesta.text, 'html.parser')
        bloques_empleo = soup.find_all('article')
        nuevos_empleos_detectados = 0
        
        for bloque in bloques_empleo:
            enlace_tag = bloque.find('a')
            if enlace_tag and enlace_tag.get('href'):
                titulo = enlace_tag.text.strip()
                link_detalle = enlace_tag['href']
                
                if len(titulo) > 15 and "html" in link_detalle:
                    if link_detalle not in enlaces_existentes:
                        
                        texto_completo = bloque.get_text()
                        dep, prov, dist = extraer_datos_geograficos(texto_completo + " " + titulo)
                        
                        print(f"\n✨ ¡Nuevo empleo detectado!: {titulo} ({dep})")
                        
                        id_interno = len(empleos_guardados) + 1
                        nombre_archivo_html = f"empleo-{id_interno}.html"
                        
                        with open(nombre_archivo_html, "w", encoding="utf-8") as html:
                            html.write(f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{titulo}</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 0; padding: 20px; background-color: #f7f9fa; color: #333; }}
        .card {{ background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); max-width: 650px; margin: 30px auto; border-top: 5px solid #d91d1d; }}
        h1 {{ color: #d91d1d; font-size: 22px; margin-top: 0; }}
        .info-box {{ background: #f1f5f9; padding: 15px; border-radius: 8px; margin: 20px 0; font-size: 15px; }}
        .geo {{ color: #64748b; font-weight: bold; font-size: 13px; text-transform: uppercase; }}
        .btn {{ display: block; text-align: center; background: #22c55e; color: white; padding: 14px; text-decoration: none; border-radius: 6px; font-weight: bold; margin-top: 25px; font-size: 16px; }}
    </style>
</head>
<body>
    <div class="card">
        <span class="geo">📍 Región: {dep}</span>
        <h1>{titulo}</h1>
        
        <div class="info-box">
            <p><strong>Ubicación Geográfica:</strong> Asignada a la región de {dep}.</p>
            <p>Se ha detectado una plaza vigente para esta entidad pública. Usa el botón oficial de abajo para ingresar directamente al portal del Estado donde se procesa la postulación.</p>
        </div>
        
        <a class="btn" href="{link_detalle}" target="_blank">🔗 Ingresar a la Publicación Oficial del Estado</a>
    </div>
</body>
</html>""")
                        
                        empleos_guardados.append({
                            "id_interno": id_interno,
                            "titulo": titulo,
                            "enlace_origen": link_detalle,
                            "archivo_web": nombre_archivo_html,
                            "ubicacion": {
                                "departamento": dep,
                                "provincia": prov,
                                "distrito": dist
                            }
                        })
                        
                        publicar_en_facebook(titulo, nombre_archivo_html, dep)
                        nuevos_empleos_detectados += 1
                        
                        if nuevos_empleos_detectados >= 10:
                            break
                            
        if nuevos_empleos_detectados > 0:
            guardar_empleos(empleos_guardados)
            print(f"\n✅ ¡Éxito! Se generaron {nuevos_empleos_detectados} páginas web en tu repositorio.")
        else:
            print("\n😴 No hay novedades de empleos en este instante.")
            
        # Llamamos siempre a actualizar el index.html al finalizar, haya o no nuevos empleos
        generar_portada_principal(empleos_guardados)
            
    except Exception as e:
        print(f"💥 Ocurrió un inconveniente: {e}")

if __name__ == "__main__":
    procesar_convocatorias()