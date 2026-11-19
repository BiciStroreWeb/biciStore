from django.test import TestCase
from django.urls import reverse


class PaginasPublicasTests(TestCase):
    def test_paginas_principales_responden(self):
        for nombre_url in ("inicio", "productos", "accesorios", "resenas", "contacto"):
            with self.subTest(nombre_url=nombre_url):
                respuesta = self.client.get(reverse(nombre_url))
                self.assertEqual(respuesta.status_code, 200)
                self.assertContains(respuesta, "BiciStore")

    def test_filtro_de_productos(self):
        respuesta = self.client.get(reverse("productos"), {"categoria": "montana"})
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Trek Marlin 7 Gen 3")
        self.assertNotContains(respuesta, "Giant Contend AR 1")

    def test_formulario_de_contacto(self):
        respuesta = self.client.post(
            reverse("contacto"),
            {
                "nombre": "Ana",
                "correo": "ana@example.com",
                "asunto": "Consulta",
                "mensaje": "Quiero información.",
            },
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "enviado correctamente")

    def test_formulario_de_resena(self):
        respuesta = self.client.post(reverse("resenas"), {"opinion": "Excelente bicicleta."})
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Gracias por compartir")
