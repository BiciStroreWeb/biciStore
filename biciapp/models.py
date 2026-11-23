from django.db import models
from django.conf import settings


class Bicicleta(models.Model):
    nombre = models.CharField(max_length=100)
    marca = models.CharField(max_length=100)
    categoria = models.CharField(max_length=50)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    descripcion = models.TextField()
    imagen = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.nombre


class Resena(models.Model):
    estrellas = models.PositiveSmallIntegerField(default=5)
    texto = models.TextField()
    autor = models.CharField(max_length=100, default="Cliente")
    compra = models.CharField(max_length=150, blank=True)
    creada_en = models.DateTimeField(auto_now_add=True)
    actualizada_en = models.DateTimeField(auto_now=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="resenas_bicistore"
    )

    class Meta:
        ordering = ["-creada_en", "-id"]
        verbose_name = "reseña"
        verbose_name_plural = "reseñas"

    def __str__(self):
        return f"{self.autor}: {self.texto[:50]}"

    @property
    def estrellas_visual(self):
        return "★" * self.estrellas + "☆" * (5 - self.estrellas)
