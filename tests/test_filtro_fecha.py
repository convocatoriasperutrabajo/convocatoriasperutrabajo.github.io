import unittest

from filtro_fecha import dias_desde_publicacion, es_publicacion_reciente


class FiltroFechaTests(unittest.TestCase):
    def test_acepta_hasta_siete_dias(self):
        self.assertTrue(es_publicacion_reciente("Publicado hoy"))
        self.assertTrue(es_publicacion_reciente("Hace 7 días"))
        self.assertEqual(dias_desde_publicacion("Actualizado ayer"), 1)

    def test_rechaza_mas_de_siete_dias(self):
        self.assertFalse(es_publicacion_reciente("Hace 8 días"))
        self.assertFalse(es_publicacion_reciente("Hace 2 semanas"))
        self.assertFalse(es_publicacion_reciente("Hace más de 15 días"))


if __name__ == "__main__":
    unittest.main()
