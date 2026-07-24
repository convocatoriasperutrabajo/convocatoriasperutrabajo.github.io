# Empleos en Cañete

Sitio estático que reúne ofertas de los últimos 7 días de Computrabajo, Indeed, LinkedIn y Bumeran para los 16 distritos de la provincia de Cañete. Publica información resumida, separa los avisos por distrito y dirige siempre al aviso individual original.

## Actualización automática

GitHub Actions ejecuta diariamente `scraper.py`, consulta las cuatro fuentes y regenera el sitio. La lista se conserva en `empleos.json`; cada oferta recibe un identificador estable basado en entidad, referencia, puesto y ubicación. Los avisos con más de 7 días se eliminan.

Si una fuente bloquea temporalmente la consulta, el actualizador conserva sus ofertas anteriores. Antes de guardar cambios, `validar_sitio.py` comprueba que no haya IDs duplicados, fichas faltantes ni enlaces que no conduzcan a avisos individuales de Computrabajo, Indeed o LinkedIn.

## Uso local

```powershell
pip install -r requirements.txt
python scraper.py --max-paginas 2 --max-documentos 0
python generar_sitio.py
```

## Límites de la fuente

No se intenta resolver CAPTCHA ni eludir controles de los portales. Si una fuente bloquea las consultas automáticas, el flujo conserva los datos que ya existen para no dejar el sitio vacío.
