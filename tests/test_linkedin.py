import unittest

from scraper_linkedin import detectar_distrito, extraer_ofertas_html


class LinkedInTests(unittest.TestCase):
    def test_extrae_aviso_individual_de_canete(self):
        pagina = """
        <li>
          <div class="base-card">
            <a class="base-card__full-link" href="https://pe.linkedin.com/jobs/view/operario-at-empresa-123?position=1"></a>
            <h3 class="base-search-card__title">Operario de producción</h3>
            <h4 class="base-search-card__subtitle">Empresa Ejemplo</h4>
            <span class="job-search-card__location">Chilca, Lima, Perú</span>
            <time>Hace 2 días</time>
          </div>
        </li>
        """
        ofertas = extraer_ofertas_html(pagina)
        self.assertEqual(len(ofertas), 1)
        self.assertEqual(ofertas[0]["fuente"], "LinkedIn")
        self.assertEqual(ofertas[0]["distrito"], "CHILCA")
        self.assertEqual(ofertas[0]["url_postulacion"], "https://pe.linkedin.com/jobs/view/operario-at-empresa-123")

    def test_no_confunde_san_luis_de_lima(self):
        self.assertEqual(detectar_distrito("San Luis, Lima, Perú", "Analista"), "")


if __name__ == "__main__":
    unittest.main()
