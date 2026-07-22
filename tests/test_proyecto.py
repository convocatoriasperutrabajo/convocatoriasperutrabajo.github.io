import unittest
from datetime import date

from empleo_utils import asegurar_id, nombre_archivo_oferta
from scraper import retirar_ofertas_vencidas
from validar_sitio import es_url_oficial


OFERTA = {
    "titulo": "TÃ‰CNICO/A EN GESTIÃ“N III",
    "entidad": "ENTIDAD DE PRUEBA",
    "ubicacion": "CUSCO - CUSCO",
    "numero_convocatoria": "CAS-001",
}


class ProyectoTests(unittest.TestCase):
    def test_id_y_nombre_de_ficha_son_estables(self):
        primera = asegurar_id(OFERTA)
        segunda = asegurar_id(dict(reversed(list(OFERTA.items()))))
        self.assertEqual(primera["id"], segunda["id"])
        self.assertEqual(nombre_archivo_oferta(primera), nombre_archivo_oferta(segunda))
        self.assertIn("tecnico-a-en-gestion-iii", nombre_archivo_oferta(primera))

    def test_solo_acepta_dominios_del_estado(self):
        self.assertTrue(es_url_oficial("https://app.servir.gob.pe/ruta"))
        self.assertTrue(es_url_oficial("https://www.gob.pe/institucion/servir"))
        self.assertFalse(es_url_oficial("https://convocatorias-ejemplo.com/aviso"))
        self.assertFalse(es_url_oficial("https://gob.pe.sitio-falso.com/aviso"))

    def test_retira_solo_convocatorias_vencidas(self):
        empleos = {
            "vencida": {"fecha_fin": "21/07/2026"},
            "vigente": {"fecha_fin": "22/07/2026"},
            "sin_fecha": {"fecha_fin": ""},
        }
        self.assertEqual(retirar_ofertas_vencidas(empleos, date(2026, 7, 22)), 1)
        self.assertEqual(set(empleos), {"vigente", "sin_fecha"})


if __name__ == "__main__":
    unittest.main()
