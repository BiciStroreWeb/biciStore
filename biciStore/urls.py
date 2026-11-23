from django.contrib import admin
from django.urls import path

from biciapp import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.inicio, name="inicio"),
    path("productos/", views.productos, name="productos"),
    path("carrito/", views.carrito, name="carrito"),
    path("carrito/agregar/<str:producto_id>/", views.agregar_carrito, name="agregar_carrito"),
    path("carrito/actualizar/", views.actualizar_carrito, name="actualizar_carrito"),
    path("carrito/quitar/<str:producto_id>/", views.quitar_carrito, name="quitar_carrito"),
    path("checkout/", views.checkout, name="checkout"),
    path("accesorios/", views.accesorios, name="accesorios"),
    path("resenas/", views.resenas, name="resenas"),
    path("resenas/<int:resena_id>/editar/", views.editar_resena, name="editar_resena"),
    path("resenas/<int:resena_id>/eliminar/", views.eliminar_resena, name="eliminar_resena"),
    path("contacto/", views.contacto, name="contacto"),
    path("registro/", views.registro, name="registro"),
    path("iniciar-sesion/", views.iniciar_sesion, name="iniciar_sesion"),
    path("perfil/", views.perfil, name="perfil"),
    path("cerrar-sesion/", views.cerrar_sesion, name="cerrar_sesion"),
]
