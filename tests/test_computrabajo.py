import unittest

from scraper_computrabajo import extraer_ofertas_html


class ComputrabajoTests(unittest.TestCase):
    def test_extrae_tarjeta_con_enlace_individual(self):
        pagina = """
        <article>
          <h2><a href="/ofertas-de-trabajo/oferta-de-trabajo-de-operario-en-chilca-ABC123">
            Operario de producción
          </a></h2>
          <p><a href="https://pe.computrabajo.com/empresas/empresa-ejemplo">Empresa Ejemplo</a></p>
          <p>Chilca, Lima</p>
          <span>S/. 1.500,00 (Mensual)</span>
          <p>Hace 2 horas</p>
        </article>
        """
        ofertas = extraer_ofertas_html(pagina)
        self.assertEqual(len(ofertas), 1)
        self.assertEqual(ofertas[0]["distrito"], "CHILCA")
        self.assertEqual(ofertas[0]["fuente"], "Computrabajo Perú")
        self.assertIn("/ofertas-de-trabajo/", ofertas[0]["url_postulacion"])


if __name__ == "__main__":
    unittest.main()
