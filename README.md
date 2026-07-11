# Convocatorias de Trabajo

Sitio estático que difunde convocatorias del portal oficial Talento Perú (SERVIR). Cada ficha dirige al portal oficial para revisar requisitos y postular.

## Actualización automática

GitHub Actions ejecuta diariamente `scraper.py`, regenera el sitio y publica solo las convocatorias no publicadas antes en Facebook. La lista se conserva en `empleos.json`; cada convocatoria recibe un identificador estable basado en entidad, número, puesto y ubicación, por lo que no se mezclan números repetidos de entidades distintas. También conserva el Word oficial de las convocatorias nuevas, para que cada ficha tenga una descarga directa.

## Uso local

```powershell
pip install -r requirements.txt
python scraper.py --max-paginas 2
python generar_sitio.py
python facebook_poster.py --dry-run
```

Para publicar en Facebook, crea un archivo `.env` desde `.env.example` y completa los valores. Nunca subas ese archivo al repositorio.

## Límites de la fuente

No se intenta ocultar la automatización, resolver CAPTCHA ni eludir controles del portal. Si SERVIR bloquea las consultas automáticas, se debe solicitar acceso o un canal de datos autorizado a la entidad, o importar datos desde una fuente oficial permitida. El flujo conserva los datos que ya existen si una consulta falla, para no dejar el sitio vacío.
