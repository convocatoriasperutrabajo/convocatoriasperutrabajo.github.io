# Convocatorias de Trabajo

Sitio estÃ¡tico que difunde Ãºnicamente convocatorias obtenidas del portal oficial Talento PerÃº (SERVIR). No consume avisos de bolsas de trabajo ni de pÃ¡ginas agregadoras. Cada ficha conserva el documento de la convocatoria cuando estÃ¡ disponible y enlaza a la fuente oficial del Estado.

## ActualizaciÃ³n automÃ¡tica

GitHub Actions ejecuta diariamente `scraper.py`, regenera el sitio y publica solo las convocatorias no publicadas antes en Facebook. La lista se conserva en `empleos.json`; cada convocatoria recibe un identificador estable basado en entidad, nÃºmero, puesto y ubicaciÃ³n, por lo que no se mezclan nÃºmeros repetidos de entidades distintas. TambiÃ©n conserva el Word oficial de las convocatorias nuevas, para que cada ficha tenga una descarga directa.

Antes de guardar cambios, `validar_sitio.py` comprueba que no haya IDs duplicados, fichas faltantes, documentos rotos ni enlaces a dominios ajenos al Estado.

## Uso local

```powershell
pip install -r requirements.txt
python scraper.py --max-paginas 2
python generar_sitio.py
python facebook_poster.py --dry-run
```

Para publicar en Facebook, crea un archivo `.env` desde `.env.example` y completa los valores. Nunca subas ese archivo al repositorio.

## LÃ­mites de la fuente

No se intenta ocultar la automatizaciÃ³n, resolver CAPTCHA ni eludir controles del portal. Si SERVIR bloquea las consultas automÃ¡ticas, se debe solicitar acceso o un canal de datos autorizado a la entidad, o importar datos desde una fuente oficial permitida. El flujo conserva los datos que ya existen si una consulta falla, para no dejar el sitio vacÃ­o.
