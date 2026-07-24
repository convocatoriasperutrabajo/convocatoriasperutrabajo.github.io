import unittest

from scraper_bumeran import extraer_ofertas_html


class BumeranTests(unittest.TestCase):
    def test_extrae_aviso_reciente_individual(self):
        pagina = """
        <article>
          <p>Publicado hace 3 días</p>
          <h2><a href="/empleos/ejecutivo-de-operaciones-tienda-mala-lima-caja-ica-1118339367.html">
            Ejecutivo de Operaciones Tienda Mala
          </a></h2>
          <p>Mala, Lima</p>
        </article>
        """
        ofertas = extraer_ofertas_html(pagina, "MALA")
        self.assertEqual(len(ofertas), 1)
        self.assertEqual(ofertas[0]["fuente"], "Bumeran Perú")
        self.assertEqual(ofertas[0]["distrito"], "MALA")
        self.assertIn("/empleos/", ofertas[0]["url_postulacion"])

    def test_descarta_aviso_de_mas_de_una_semana(self):
        pagina = """
        <article>
          <p>Actualizado hace 8 días</p>
          <h2><a href="/empleos/aviso-antiguo-123.html">Aviso antiguo</a></h2>
          <p>Mala, Lima</p>
        </article>
        """
        self.assertEqual(extraer_ofertas_html(pagina, "MALA"), [])


if __name__ == "__main__":
    unittest.main()
