from django.contrib import admin
from .models import Bicicleta, Resena


@admin.register(Resena)
class ResenaAdmin(admin.ModelAdmin):
    list_display = ("autor", "estrellas", "compra", "creada_en", "actualizada_en")
    list_filter = ("estrellas",)
    search_fields = ("autor", "texto", "compra")


admin.site.register(Bicicleta)
