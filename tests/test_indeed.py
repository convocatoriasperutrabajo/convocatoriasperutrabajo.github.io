import unittest

from scraper_indeed import extraer_ofertas_html


class IndeedTests(unittest.TestCase):
    def test_extrae_aviso_individual_del_distrito(self):
        pagina = """
        <div class="job_seen_beacon">
          <h2 class="jobTitle"><a class="jcs-JobTitle" data-jk="ABC123" href="/rc/clk?jk=ABC123">Técnico de almacén</a></h2>
          <span data-testid="company-name">Empresa Ejemplo</span>
          <div data-testid="text-location">Mala, Lima</div>
          <span class="salaryText">S/. 1,500 por mes</span>
          <span class="date">Hace 2 días</span>
        </div>
        """
        ofertas = extraer_ofertas_html(pagina, "MALA")
        self.assertEqual(len(ofertas), 1)
        self.assertEqual(ofertas[0]["fuente"], "Indeed Perú")
        self.assertEqual(ofertas[0]["distrito"], "MALA")
        self.assertEqual(ofertas[0]["url_postulacion"], "https://pe.indeed.com/viewjob?jk=ABC123")

    def test_descarta_otro_distrito(self):
        pagina = """
        <div class="job_seen_beacon">
          <h2><a data-jk="XYZ" href="/viewjob?jk=XYZ">Trabajo remoto</a></h2>
          <div data-testid="text-location">Lima, Lima</div>
        </div>
        """
        self.assertEqual(extraer_ofertas_html(pagina, "MALA"), [])


if __name__ == "__main__":
    unittest.main()
