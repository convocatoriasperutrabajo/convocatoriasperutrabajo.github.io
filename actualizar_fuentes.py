"""Actualiza las fuentes privadas sin borrar resultados previos cuando una web bloquea el acceso."""

import json
from datetime import date, datetime
from pathlib import Path

from scraper_computrabajo import recopilar_computrabajo
from scraper_indeed import recopilar_indeed
from scraper_linkedin import recopilar_linkedin
from scraper_bumeran import recopilar_bumeran


ARCHIVO = Path("empleos.json")
FUENTES = {
    "Computrabajo Perú": recopilar_computrabajo,
    "Indeed Perú": recopilar_indeed,
    "LinkedIn": recopilar_linkedin,
    "Bumeran Perú": recopilar_bumeran,
}


def cargar_existentes() -> list[dict]:
    if not ARCHIVO.exists():
        return []
    return json.loads(ARCHIVO.read_text(encoding="utf-8"))


def ejecutar_fuentes(headless: bool = True) -> None:
    existentes = cargar_existentes()
    por_fuente = {
        fuente: [oferta for oferta in existentes if oferta.get("fuente") == fuente]
        for fuente in FUENTES
    }

    for fuente, recopilador in FUENTES.items():
        try:
            nuevas = recopilador(headless=headless)
            if nuevas:
                por_fuente[fuente] = nuevas
                print(f"✅ {fuente}: {len(nuevas)} ofertas encontradas")
            else:
                print(f"⚠️ {fuente} no devolvió resultados; se conserva su publicación anterior")
        except Exception as error:
            print(f"⚠️ {fuente} no estuvo disponible: {error}")
            print("   Se conserva su publicación anterior.")

    unicas = {}
    for ofertas in por_fuente.values():
        for oferta in ofertas:
            try:
                publicada = datetime.strptime(oferta["fecha_inicio"], "%d/%m/%Y").date()
            except (KeyError, TypeError, ValueError):
                continue
            if 0 <= (date.today() - publicada).days <= 7:
                unicas[oferta["url_oficial"]] = oferta

    if not unicas:
        raise RuntimeError("Ninguna fuente devolvió empleos y no existe una publicación anterior")

    ARCHIVO.write_text(
        json.dumps(list(unicas.values()), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"✅ {len(unicas)} ofertas guardadas entre todas las fuentes")
