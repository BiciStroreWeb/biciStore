import re
import uuid
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404, redirect, render

from .models import Bicicleta, Resena


PRODUCTOS = [
    {"nombre": "Trek Marlin 7 Gen 3", "categoria": "montana", "categoria_nombre": "Montaña", "descripcion": "Bicicleta de montaña ideal para senderos y terrenos difíciles. Ofrece gran control y estabilidad.", "caracteristicas": ["12 velocidades", "Suspensión delantera", "Cuadro de montaña"], "precio": Decimal("29999.00"), "imagen": "trek-marlin.jpg"},
    {"nombre": "Specialized Rockhopper", "categoria": "montana", "categoria_nombre": "Montaña", "descripcion": "Una bicicleta de montaña versátil para disfrutar de caminos y senderos.", "caracteristicas": ["18 velocidades", "Suspensión delantera", "Bicicleta MTB"], "precio": Decimal("18999.00"), "imagen": "specialized-rockhopper.jpg"},
    {"nombre": "Giant Contend AR 1", "categoria": "carretera", "categoria_nombre": "Carretera", "descripcion": "Bicicleta de carretera cómoda y rápida, perfecta para recorrer largas distancias.", "caracteristicas": ["22 velocidades", "Cuadro ligero", "Diseñada para carretera"], "precio": Decimal("39999.00"), "imagen": "giant-contend.jpg"},
    {"nombre": "Cannondale Quick 4", "categoria": "ciudad", "categoria_nombre": "Ciudad", "descripcion": "Bicicleta urbana cómoda y práctica para desplazamientos diarios por la ciudad.", "caracteristicas": ["9 velocidades", "Uso urbano", "Cuadro ligero"], "precio": Decimal("17999.00"), "imagen": "cannondale-quick.jpg"},
    {"nombre": "Trek Domane AL 2 Gen 4", "categoria": "carretera", "categoria_nombre": "Carretera", "descripcion": "Bicicleta de carretera diseñada para ofrecer comodidad y velocidad durante recorridos largos.", "caracteristicas": ["16 velocidades", "Cuadro de aluminio", "Uso de carretera"], "precio": Decimal("29999.00"), "imagen": "trek-domane.jpg"},
    {"nombre": "Cannondale Trail 5", "categoria": "montana", "categoria_nombre": "Montaña", "descripcion": "Bicicleta de montaña preparada para caminos, senderos y recorridos recreativos.", "caracteristicas": ["10 velocidades", "Suspensión delantera", "Bicicleta MTB"], "precio": Decimal("22999.00"), "imagen": "cannondale-trail.jpg"},
]

CATEGORIAS = [
    {"slug": "montana", "nombre": "Montaña", "icono": "🏔️"},
    {"slug": "ciudad", "nombre": "Ciudad", "icono": "🏙️"},
    {"slug": "carretera", "nombre": "Carretera", "icono": "🛣️"},
]

ACCESORIOS = [
    {"nombre": "Casco Deportivo", "icono": "⛑️", "descripcion": "Casco ligero y cómodo para protegerte durante tus recorridos.", "precio": "$899 MXN"},
    {"nombre": "Luces LED", "icono": "💡", "descripcion": "Juego de luces delanteras y traseras para mejorar tu visibilidad durante la noche.", "precio": "$499 MXN"},
    {"nombre": "Guantes de Ciclismo", "icono": "🧤", "descripcion": "Guantes cómodos con protección para tus manos durante recorridos largos.", "precio": "$399 MXN"},
    {"nombre": "Bolsa para Bicicleta", "icono": "🎒", "descripcion": "Bolsa compacta para transportar herramientas, celular y objetos personales.", "precio": "$599 MXN"},
    {"nombre": "Candado de Seguridad", "icono": "🔒", "descripcion": "Candado resistente para mantener tu bicicleta protegida.", "precio": "$699 MXN"},
    {"nombre": "Portabotella", "icono": "🥤", "descripcion": "Soporte para transportar tu botella de agua durante tus recorridos.", "precio": "$249 MXN"},
]


def _catalogo():
    bicicletas_db = list(Bicicleta.objects.all())
    if bicicletas_db:
        return [{
            "id": f"db-{bici.id}", "nombre": bici.nombre, "marca": bici.marca,
            "categoria": bici.categoria.strip().lower(),
            "categoria_nombre": bici.categoria, "precio": bici.precio,
            "descripcion": bici.descripcion, "caracteristicas": [],
            "imagen": bici.imagen.rsplit("/", 1)[-1] if bici.imagen else "trek-marlin.jpg",
        } for bici in bicicletas_db]
    return [{**producto, "id": f"demo-{indice}", "marca": producto["nombre"].split()[0]}
            for indice, producto in enumerate(PRODUCTOS)]


def _carrito_productos(request):
    carrito = request.session.get("carrito", {})
    catalogo = {producto["id"]: producto for producto in _catalogo()}
    lineas, total, cantidad = [], Decimal("0"), 0
    carrito_limpio = {}
    for producto_id, cantidad_str in carrito.items():
        producto = catalogo.get(producto_id)
        try:
            cantidad_item = max(0, int(cantidad_str))
        except (TypeError, ValueError):
            cantidad_item = 0
        if not producto or cantidad_item == 0:
            continue
        subtotal = producto["precio"] * cantidad_item
        lineas.append({"producto": producto, "cantidad": cantidad_item, "subtotal": subtotal})
        total += subtotal
        cantidad += cantidad_item
        carrito_limpio[producto_id] = cantidad_item
    request.session["carrito"] = carrito_limpio
    return lineas, total, cantidad


def inicio(request):
    return render(request, "biciapp/index.html", {"categorias": CATEGORIAS})


def productos(request):
    categoria = request.GET.get("categoria", "").strip().lower()
    categorias_validas = {item["slug"] for item in CATEGORIAS}
    productos_db = _catalogo()
    if categoria in categorias_validas:
        productos_filtrados = [p for p in productos_db if p["categoria"] == categoria]
        categoria_actual = next(item for item in CATEGORIAS if item["slug"] == categoria)
        titulo = f"Bicicletas de {categoria_actual['nombre'].lower()}" if categoria != "ciudad" else "Bicicletas para ciudad"
        descripcion = {"montana": "Modelos diseñados para senderos, caminos y terrenos difíciles.", "ciudad": "Modelos cómodos y prácticos para tus recorridos diarios.", "carretera": "Bicicletas ligeras diseñadas para velocidad y largas distancias."}[categoria]
    else:
        categoria = ""
        productos_filtrados = productos_db
        titulo = "Catálogo de bicicletas"
        descripcion = "Descubre algunos de los modelos más populares de bicicletas."
    return render(request, "biciapp/productos.html", {"productos": productos_filtrados, "categorias": CATEGORIAS, "categoria_actual": categoria, "titulo": titulo, "descripcion": descripcion})


def agregar_carrito(request, producto_id):
    if request.method != "POST":
        return redirect("productos")
    ids_validos = {producto["id"] for producto in _catalogo()}
    if producto_id not in ids_validos:
        messages.error(request, "La bicicleta seleccionada ya no está disponible.")
        return redirect("productos")
    carrito = request.session.get("carrito", {})
    carrito[producto_id] = int(carrito.get(producto_id, 0)) + 1
    request.session["carrito"] = carrito
    messages.success(request, "La bicicleta se agregó al carrito.")
    return redirect(request.POST.get("next") or "productos")


def carrito(request):
    lineas, total, cantidad = _carrito_productos(request)
    return render(request, "biciapp/carrito.html", {"lineas": lineas, "total": total, "cantidad": cantidad})


def actualizar_carrito(request):
    if request.method == "POST":
        carrito = request.session.get("carrito", {})
        producto_quitar = request.POST.get("quitar")
        if producto_quitar:
            carrito.pop(producto_quitar, None)
            request.session["carrito"] = carrito
            messages.success(request, "Producto eliminado del carrito.")
            return redirect("carrito")
        for producto_id in list(carrito):
            try:
                nueva_cantidad = max(0, min(99, int(request.POST.get(f"cantidad_{producto_id}", carrito[producto_id]))))
            except (TypeError, ValueError):
                nueva_cantidad = carrito[producto_id]
            if nueva_cantidad:
                carrito[producto_id] = nueva_cantidad
            else:
                carrito.pop(producto_id, None)
        request.session["carrito"] = carrito
        messages.success(request, "El carrito se actualizó.")
    return redirect("carrito")


def quitar_carrito(request, producto_id):
    if request.method == "POST":
        carrito = request.session.get("carrito", {})
        carrito.pop(producto_id, None)
        request.session["carrito"] = carrito
        messages.success(request, "Producto eliminado del carrito.")
    return redirect("carrito")


def checkout(request):
    lineas, total, cantidad = _carrito_productos(request)
    if not lineas:
        messages.error(request, "Agrega al menos una bicicleta antes de continuar.")
        return redirect("carrito")
    if request.method == "POST":
        nombre = request.POST.get("nombre", "").strip()
        correo = request.POST.get("correo", "").strip()
        numero = re.sub(r"\s+", "", request.POST.get("numero_tarjeta", ""))
        vencimiento = request.POST.get("vencimiento", "").strip()
        cvv = request.POST.get("cvv", "").strip()
        errores = []
        if len(nombre) < 2:
            errores.append("Escribe el nombre del comprador.")
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", correo):
            errores.append("Escribe un correo electrónico válido.")
        if not re.fullmatch(r"\d{13,19}", numero):
            errores.append("El número de tarjeta debe contener sólo entre 13 y 19 dígitos.")
        if not re.fullmatch(r"(0[1-9]|1[0-2])\/\d{2}", vencimiento):
            errores.append("La fecha debe usar el formato MM/AA.")
        if not re.fullmatch(r"\d{3,4}", cvv):
            errores.append("El CVV debe contener sólo 3 o 4 dígitos.")
        if errores:
            for error in errores:
                messages.error(request, error)
            return render(request, "biciapp/checkout.html", {"lineas": lineas, "total": total, "cantidad": cantidad})
        folio = uuid.uuid4().hex[:10].upper()
        detalle = "\n".join(f"- {linea['producto']['nombre']} x {linea['cantidad']}: ${linea['subtotal']:,.2f} MXN" for linea in lineas)
        cuerpo = f"Hola {nombre},\n\nTu compra en BiciStore fue registrada correctamente.\n\nFolio: {folio}\nComprador: {nombre}\n\nProductos:\n{detalle}\n\nTotal: ${total:,.2f} MXN"
        send_mail(f"Confirmación de compra #{folio} - BiciStore", cuerpo, settings.DEFAULT_FROM_EMAIL, [correo], fail_silently=False)
        request.session["carrito"] = {}
        return render(request, "biciapp/compra_exitosa.html", {"folio": folio, "nombre": nombre, "correo": correo, "lineas": lineas, "total": total})
    return render(request, "biciapp/checkout.html", {"lineas": lineas, "total": total, "cantidad": cantidad})


def accesorios(request):
    return render(request, "biciapp/accesorios.html", {"accesorios": ACCESORIOS})


def _datos_resena(request):
    texto = request.POST.get("texto", request.POST.get("opinion", "")).strip()
    autor = request.POST.get("autor", "Cliente").strip() or "Cliente"
    compra = request.POST.get("compra", "").strip()
    try:
        estrellas = int(request.POST.get("estrellas", 5))
    except (TypeError, ValueError):
        estrellas = 5
    return texto, autor, compra, max(1, min(5, estrellas))


def resenas(request):
    if request.method == "POST":
        texto, autor, compra, estrellas = _datos_resena(request)
        if texto:
            Resena.objects.create(texto=texto, autor=autor, compra=compra, estrellas=estrellas)
            messages.success(request, "Gracias por compartir tu experiencia. Tu reseña se guardó correctamente.")
        else:
            messages.error(request, "Escribe una reseña antes de enviarla.")
    return render(request, "biciapp/resenas.html", {"resenas": Resena.objects.all()})


def editar_resena(request, resena_id):
    resena = get_object_or_404(Resena, pk=resena_id)
    if request.method == "POST":
        texto, autor, compra, estrellas = _datos_resena(request)
        if texto:
            resena.texto, resena.autor, resena.compra, resena.estrellas = texto, autor, compra, estrellas
            resena.save()
            messages.success(request, "La reseña se actualizó correctamente.")
            return redirect("resenas")
        messages.error(request, "La reseña no puede quedar vacía.")
    return render(request, "biciapp/editar_resena.html", {"resena": resena})


def eliminar_resena(request, resena_id):
    resena = get_object_or_404(Resena, pk=resena_id)
    if request.method == "POST":
        resena.delete()
        messages.success(request, "La reseña se eliminó correctamente.")
    return redirect("resenas")


def contacto(request):
    datos = {campo: request.POST.get(campo, "").strip() for campo in ("nombre", "correo", "asunto", "mensaje")}
    if request.method == "GET" and request.GET.get("producto", "").strip():
        datos["asunto"] = f"Información sobre {request.GET['producto'].strip()}"
    if request.method == "POST":
        if all(datos.values()):
            messages.success(request, "Tu mensaje fue enviado correctamente. Te responderemos pronto.")
            datos = {campo: "" for campo in datos}
        else:
            messages.error(request, "Completa todos los campos para enviar tu mensaje.")
    return render(request, "biciapp/contacto.html", {"datos": datos})
