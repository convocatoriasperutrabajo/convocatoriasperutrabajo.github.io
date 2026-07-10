import os
import json
import requests
from bs4 import BeautifulSoup

# ==========================================
# CONFIGURACIÓN DE TU PÁGINA DE FACEBOOK
# ==========================================
# (Obtendremos estos datos en el siguiente paso)
FB_PAGE_ID = "AQUÍ_VA_EL_ID_DE_TU_PÁGINA"
FB_ACCESS_TOKEN = "AQUÍ_VA_TU_TOKEN_DE_ACCESO"
# ==========================================

URL = "https://www.convocatoriasdetrabajo.com/"
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

def publicar_en_facebook(titulo, nombre_archivo_web):
    """Envía la publicación automáticamente a Facebook usando la API oficial."""
    # Cuando lo subamos a GitHub, tu web tendrá este enlace base gratuito
    # Reemplaza 'tu-usuario' por tu nombre de usuario de GitHub real más adelante
    enlace_mi_web = f"https://tu-usuario.github.io/bot-empleos/{nombre_archivo_web}"
    
    mensaje = f"📢 ¡Nueva Convocatoria Laboral del Estado! 💼\n\n📌 {titulo}\n\n👇 Revisa los requisitos completos y postula aquí:"
    
    url_fb = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/feed"
    payload = {
        "message": mensaje,
        "link": enlace_mi_web,
        "access_token": FB_ACCESS_TOKEN
    }
    
    print(f"📡 Intentando publicar en Facebook: {titulo}...")
    
    # Si aún no configuras los tokens, simulamos la publicación para que no dé error
    if "AQUÍ_VA_" in FB_ACCESS_TOKEN:
        print(f"   [SIMULACIÓN] Post enviado a Facebook con éxito -> {enlace_mi_web}")
        return
        
    try:
        respuesta = requests.post(url_fb, data=payload, timeout=10)
        if respuesta.status_code == 200:
            print("✅ ¡Publicado en tu Facebook exitosamente!")
        else:
            print(f"❌ Error al publicar en Facebook: {respuesta.text}")
    except Exception as e:
        print(f"💥 Falló la conexión con la API de Facebook: {e}")

def extraer_y_guardar_empleos():
    print("🔍 Buscando empleos nuevos y generando páginas web...")
    empleos_guardados = cargar_empleos_guardados()
    enlaces_existentes = [emp["enlace"] for emp in empleos_guardados]
    
    try:
        respuesta = requests.get(URL, headers=HEADERS, timeout=10)
        if respuesta.status_code != 200:
            print(f"❌ Error al acceder a la página: {respuesta.status_code}")
            return
        
        soup = BeautifulSoup(respuesta.text, 'html.parser')
        bloques_empleo = soup.find_all('article')
        
        nuevos_empleos_detectados = 0
        
        for bloque in bloques_empleo:
            enlace_tag = bloque.find('a')
            if enlace_tag and enlace_tag.get('href'):
                titulo = enlace_tag.text.strip()
                link = enlace_tag['href']
                
                if len(titulo) > 15 and "html" in link:
                    if link not in enlaces_existentes:
                        print(f"\n✨ ¡Nuevo empleo detectado!: {titulo}")
                        
                        id_empleo = len(empleos_guardados) + 1
                        nombre_archivo_html = f"empleo-{id_empleo}.html"
                        
                        # Crear el HTML para tu web
                        with open(nombre_archivo_html, "w", encoding="utf-8") as html:
                            html.write(f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{titulo} - Convocatorias 2026</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; background-color: #f4f4f9; color: #333; }}
        .container {{ background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); max-width: 600px; margin: auto; }}
        h1 {{ color: #0056b3; font-size: 24px; }}
        .btn {{ display: inline-block; background: #28a745; color: white; padding: 12px 20px; text-decoration: none; border-radius: 5px; font-weight: bold; margin-top: 20px; }}
        .btn:hover {{ background: #218838; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{titulo}</h1>
        <p>Se ha publicado una nueva oportunidad laboral en el sector público.</p>
        <p>Revisa los detalles completos, requisitos y cronograma presionando el siguiente botón oficial:</p>
        <a class="btn" href="{link}" target="_blank">👉 Ver Convocatoria Completa</a>
    </div>
</body>
</html>""")
                        
                        # Registrar el empleo
                        empleos_guardados.append({
                            "id": id_empleo,
                            "titulo": titulo,
                            "enlace": link,
                            "archivo_web": nombre_archivo_html
                        })
                        
                        # 🚀 ENVIAR AUTOMÁTICAMENTE A FACEBOOK
                        publicar_en_facebook(titulo, nombre_archivo_html)
                        
                        nuevos_empleos_detectados += 1
            
            if nuevos_empleos_detectados >= 5:
                break
        
        if nuevos_empleos_detectados > 0:
            guardar_empleos(empleos_guardados)
            print(f"\n✅ ¡Proceso terminado! Se procesaron {nuevos_empleos_detectados} nuevos empleos.")
        else:
            print("\n😴 No hay novedades. Todos los empleos ya estaban registrados.")
            
    except Exception as e:
        print(f"💥 Ocurrió un error: {e}")

if __name__ == "__main__":
    extraer_y_guardar_empleos()