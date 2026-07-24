import unittest
from datetime import date

from empleo_utils import asegurar_id, es_enlace_postulacion_directo, nombre_archivo_oferta
from generar_sitio import generar_pagina_detalle
from scraper import extraer_secciones_detalle, retirar_duplicados_sin_codigo, retirar_ofertas_vencidas
from validar_sitio import es_url_oficial, es_url_postulacion_valida


OFERTA = {
    "titulo": "TÉCNICO/A EN GESTIÓN III",
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

    def test_codigo_servir_distingue_perfiles_con_el_mismo_aviso(self):
        primera = asegurar_id({**OFERTA, "codigo_servir": "797812"})
        segunda = asegurar_id({**OFERTA, "codigo_servir": "797813"})
        self.assertNotEqual(primera["id"], segunda["id"])

        empleos = {
            asegurar_id(OFERTA)["id"]: asegurar_id(OFERTA),
            primera["id"]: primera,
            segunda["id"]: segunda,
        }
        self.assertEqual(retirar_duplicados_sin_codigo(empleos), 1)
        self.assertEqual(set(empleos), {primera["id"], segunda["id"]})

    def test_solo_acepta_dominios_del_estado(self):
        self.assertTrue(es_url_oficial("https://app.servir.gob.pe/ruta"))
        self.assertTrue(es_url_oficial("https://www.gob.pe/institucion/servir"))
        self.assertFalse(es_url_oficial("https://convocatorias-ejemplo.com/aviso"))
        self.assertFalse(es_url_oficial("https://gob.pe.sitio-falso.com/aviso"))

    def test_rechaza_agregadores_como_enlace_de_postulacion(self):
        self.assertTrue(es_url_postulacion_valida("https://unajma.edu.pe/convocatoria-personal/"))
        self.assertFalse(es_url_postulacion_valida("https://convocatoriasdetrabajo.com/aviso"))
        self.assertFalse(es_enlace_postulacion_directo("https://unajma.edu.pe/convocatoria-personal/"))
        self.assertFalse(es_enlace_postulacion_directo("https://www.gob.pe/muniandresavelinocaceresdorregaray"))
        self.assertFalse(es_enlace_postulacion_directo("https://share.google/IovzweaQemtlVGF9i"))
        self.assertTrue(es_enlace_postulacion_directo("https://entidad.gob.pe/convocatorias/cas-001"))

    def test_oculta_el_word_pero_conserva_bases_reales(self):
        oferta = {
            **OFERTA,
            "vacantes": "1",
            "remuneracion": "3,000",
            "fecha_inicio": "22/07/2026",
            "fecha_fin": "31/07/2026",
            "archivo_oficial": "documentos_oficiales/portada.docx",
            "url_postulacion": "https://entidad.gob.pe/convocatoria",
            "enlaces_bases": [{"titulo": "Bases oficiales", "url": "https://entidad.gob.pe/bases.pdf"}],
        }
        pagina = generar_pagina_detalle(oferta)
        self.assertNotIn("documentos_oficiales/", pagina)
        self.assertNotIn("Talento Perú (Word)", pagina)
        self.assertIn("https://entidad.gob.pe/bases.pdf", pagina)

    def test_solo_muestra_un_boton_si_hay_enlace_directo(self):
        datos = {
            **OFERTA,
            "vacantes": "1",
            "remuneracion": "3,000",
            "fecha_inicio": "22/07/2026",
            "fecha_fin": "31/07/2026",
        }
        sin_enlace = generar_pagina_detalle(datos)
        self.assertNotIn('class="btn-fuente"', sin_enlace)
        self.assertNotIn("Ver esta convocatoria en SERVIR", sin_enlace)
        self.assertIn("no te enviaremos a un listado general", sin_enlace)

        con_enlace = generar_pagina_detalle({
            **datos,
            "url_postulacion": "https://entidad.gob.pe/convocatoria",
        })
        self.assertEqual(con_enlace.count("Ver oferta y postular"), 1)
        self.assertIn("https://entidad.gob.pe/convocatoria", con_enlace)

    def test_distingue_consulta_general_de_postulacion_directa(self):
        oferta = {
            **OFERTA,
            "vacantes": "1",
            "remuneracion": "3,000",
            "fecha_inicio": "22/07/2026",
            "fecha_fin": "31/07/2026",
            "codigo_servir": "798049",
            "url_consulta": "https://share.google/IovzweaQemtlVGF9i",
        }
        pagina = generar_pagina_detalle(oferta)
        self.assertNotIn("Ver oferta y postular", pagina)
        self.assertIn("Buscar en el portal de la institución", pagina)
        self.assertIn("apps.diresamdd.gob.pe", pagina)
        self.assertIn("798049", pagina)

    def test_extrae_requisitos_del_detalle_de_servir(self):
        texto = (
            "REQUERIMIENTO: Título profesional EXPERIENCIA: Cinco años "
            "FORMACIÓN ACADÉMICA - PERFIL: Licenciado ESPECIALIZACIÓN: Maestría "
            "CONOCIMIENTO: NO APLICA COMPETENCIAS: Trabajo en equipo "
            "DETALLE: https://entidad.gob.pe/bases CANTIDAD DE VACANTES: 1"
        )
        detalle = extraer_secciones_detalle(texto)
        self.assertEqual(detalle["requerimiento"], "Título profesional")
        self.assertEqual(detalle["experiencia"], "Cinco años")
        self.assertNotIn("conocimiento", detalle)

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
