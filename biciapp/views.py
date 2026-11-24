import json
import re
import uuid
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.contrib.auth.models import User
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render

from .models import Bicicleta, Resena


def _enviar_correo_brevo(destinatario, asunto, cuerpo):
    """Envía un correo transaccional mediante la API HTTP de Brevo."""
    if not settings.BREVO_API_KEY:
        raise RuntimeError("Falta configurar BREVO_API_KEY en el entorno.")

    datos = {
        "sender": {
            "name": settings.BREVO_SENDER_NAME,
            "email": settings.BREVO_SENDER_EMAIL,
        },
        "to": [{"email": destinatario}],
        "subject": asunto,
        "textContent": cuerpo,
    }
    solicitud = Request(
        "https://api.brevo.com/v3/smtp/email",
        data=json.dumps(datos).encode("utf-8"),
        headers={
            "accept": "application/json",
            "api-key": settings.BREVO_API_KEY,
            "content-type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(solicitud, timeout=20) as respuesta:
            if respuesta.status not in (200, 201, 202):
                raise RuntimeError(f"Brevo respondió con estado {respuesta.status}.")
    except HTTPError as error:
        detalle = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Brevo rechazó el correo (HTTP {error.code}): {detalle}") from error
    except URLError as error:
        raise RuntimeError(f"No fue posible conectar con Brevo: {error.reason}") from error


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

@login_required
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

@login_required
def checkout(request):
    lineas, total, cantidad = _carrito_productos(request)
    if not lineas:
        messages.error(request, "Agrega al menos una bicicleta antes de continuar.")
        return redirect("carrito")
    if request.method == "POST":
        nombre = request.POST.get("nombre", "").strip()
        correo = request.POST.get("correo", "").strip()
        telefono = request.POST.get("telefono", "").strip()
        calle = request.POST.get("calle", "").strip()
        numero_exterior = request.POST.get("numero_exterior", "").strip()
        numero_interior = request.POST.get("numero_interior", "").strip()
        colonia = request.POST.get("colonia", "").strip()
        ciudad = request.POST.get("ciudad", "").strip()
        estado = request.POST.get("estado", "").strip()
        codigo_postal = request.POST.get("codigo_postal", "").strip()
        referencias = request.POST.get("referencias", "").strip()
        numero = re.sub(r"\s+", "", request.POST.get("numero_tarjeta", ""))
        vencimiento = request.POST.get("vencimiento", "").strip()
        cvv = request.POST.get("cvv", "").strip()
        errores = []
        if not telefono:
            errores.append("Escribe tu número de teléfono.")
        if not calle:
            errores.append("Escribe la calle de entrega.")
        if not numero_exterior:
            errores.append("Escribe el número exterior.")
        if not colonia:
            errores.append("Escribe la colonia.")
        if not ciudad:
            errores.append("Escribe la ciudad o municipio.")
        if not estado:
            errores.append("Escribe el estado.")
        if not re.fullmatch(r"\d{5}", codigo_postal):
            errores.append("El código postal debe contener 5 dígitos.")
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
        try:
            _enviar_correo_brevo(
                correo,
                f"Confirmación de compra #{folio} - BiciStore",
                cuerpo,
            )
            messages.success(request, "Tu comprobante fue enviado a tu correo electrónico.")
        except RuntimeError as error:
            # La compra de demostración continúa, pero avisamos que el correo falló.
            messages.warning(request, f"La compra se procesó, pero no pudimos enviar el correo: {error}")
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
        if not request.user.is_authenticated:
            messages.info(request, "Inicia sesión para publicar una reseña.")
            return redirect("iniciar_sesion")
        texto, autor, compra, estrellas = _datos_resena(request)
        if texto:
            Resena.objects.create(
                texto=texto,
                autor=request.user.get_full_name() or request.user.username,
                compra=compra,
                estrellas=estrellas,
                usuario=request.user,
            )
            messages.success(request, "Gracias por compartir tu experiencia. Tu reseña se guardó correctamente.")
        else:
            messages.error(request, "Escribe una reseña antes de enviarla.")
        return redirect("resenas")
    return render(request, "biciapp/resenas.html", {"resenas": Resena.objects.select_related("usuario").all()})


@login_required
def editar_resena(request, resena_id):
    resena = get_object_or_404(Resena, pk=resena_id)
    if not (request.user.is_staff or resena.usuario_id == request.user.id):
        return HttpResponseForbidden("Solo puedes editar tus propias reseñas.")
    if request.method == "POST":
        texto, autor, compra, estrellas = _datos_resena(request)
        if texto:
            resena.texto = texto
            resena.compra = compra
            resena.estrellas = estrellas
            # El cliente no puede cambiar la identidad del autor desde el formulario.
            if request.user.is_staff:
                resena.autor = autor or resena.autor
            resena.save()
            messages.success(request, "La reseña se actualizó correctamente.")
            return redirect("resenas")
        messages.error(request, "La reseña no puede quedar vacía.")
    return render(request, "biciapp/editar_resena.html", {"resena": resena})


@login_required
def eliminar_resena(request, resena_id):
    if request.method != "POST":
        return redirect("resenas")
    resena = get_object_or_404(Resena, pk=resena_id)
    if not (request.user.is_staff or resena.usuario_id == request.user.id):
        return HttpResponseForbidden("Solo puedes eliminar tus propias reseñas.")
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


def registro(request):
    if request.user.is_authenticated:
        return redirect("perfil")
    if request.method == "POST":
        nombre = request.POST.get("nombre", "").strip()
        apellidos = request.POST.get("apellidos", "").strip()
        correo = request.POST.get("correo", "").strip().lower()
        password = request.POST.get("password", "")
        confirmar = request.POST.get("confirmar_password", "")
        errores = []
        if not nombre or not apellidos:
            errores.append("Escribe tu nombre y apellidos.")
        try:
            validate_email(correo)
        except ValidationError:
            errores.append("Escribe un correo electrónico válido.")
        if correo and User.objects.filter(email__iexact=correo).exists():
            errores.append("Ya existe una cuenta registrada con ese correo.")
        if len(password) < 8:
            errores.append("La contraseña debe tener al menos 8 caracteres.")
        if password != confirmar:
            errores.append("Las contraseñas no coinciden.")
        if errores:
            for error in errores:
                messages.error(request, error)
        else:
            usuario = User.objects.create_user(
                username=correo, email=correo, password=password,
                first_name=nombre, last_name=apellidos,
            )
            cuerpo = (
                f"Hola {nombre},\n\nTu cuenta de BiciStore fue creada correctamente.\n"
                "Ya puedes iniciar sesión y disfrutar de nuestra tienda.\n\n"
                "¡Gracias por registrarte!\nEquipo BiciStore"
            )
            try:
                _enviar_correo_brevo(correo, "¡Bienvenido a BiciStore!", cuerpo)
                messages.success(request, "Tu cuenta se creó y enviamos una confirmación a tu correo.")
            except RuntimeError:
                messages.warning(request, "Tu cuenta se creó, pero no pudimos enviar el correo de confirmación.")
            return redirect("iniciar_sesion")
    return render(request, "biciapp/registro.html")


def iniciar_sesion(request):
    if request.user.is_authenticated:
        return redirect("perfil")
    if request.method == "POST":
        identificador = request.POST.get("correo", "").strip()
        password = request.POST.get("password", "")
        usuario_obj = User.objects.filter(email__iexact=identificador).first()
        username = usuario_obj.username if usuario_obj else identificador
        usuario = authenticate(request, username=username, password=password)
        if usuario is not None:
            login(request, usuario)
            if usuario.email:
                try:
                    _enviar_correo_brevo(
                        usuario.email, "Nuevo inicio de sesión - BiciStore",
                        f"Hola {usuario.first_name or usuario.username},\n\n"
                        "Se inició sesión correctamente en tu cuenta de BiciStore.\n"
                        "Si no reconoces esta actividad, cambia tu contraseña.\n\nEquipo BiciStore",
                    )
                except RuntimeError:
                    pass
            messages.success(request, "Iniciaste sesión correctamente.")
            return redirect("panel_administracion" if usuario.is_staff else "perfil")
        messages.error(request, "El correo/usuario o la contraseña son incorrectos.")
    return render(request, "biciapp/iniciar_sesion.html")


@login_required
def perfil(request):
    if request.method == "POST":
        nombre = request.POST.get("nombre", "").strip()
        apellidos = request.POST.get("apellidos", "").strip()
        correo = request.POST.get("correo", "").strip().lower()
        try:
            validate_email(correo)
        except ValidationError:
            messages.error(request, "Escribe un correo electrónico válido.")
        else:
            if User.objects.filter(email__iexact=correo).exclude(pk=request.user.pk).exists():
                messages.error(request, "Ese correo ya está asociado a otra cuenta.")
            elif not nombre or not apellidos:
                messages.error(request, "El nombre y los apellidos son obligatorios.")
            else:
                request.user.first_name = nombre
                request.user.last_name = apellidos
                request.user.email = correo
                # Si el nombre de usuario era el correo anterior, mantener ambos sincronizados.
                if "@" in request.user.username:
                    request.user.username = correo
                request.user.save()
                messages.success(request, "Tu perfil se actualizó correctamente.")
                return redirect("perfil")
    return render(request, "biciapp/perfil.html")



@login_required
def panel_administracion(request):
    """Panel privado de administración integrado en la tienda."""
    if not request.user.is_staff:
        return HttpResponseForbidden("No tienes permiso para acceder a esta sección.")
    contexto = {
        "total_clientes": User.objects.filter(is_staff=False, is_superuser=False).count(),
        "total_bicicletas": Bicicleta.objects.count(),
        "total_resenas": Resena.objects.count(),
        "resenas": Resena.objects.select_related("usuario").all()[:50],
    }
    return render(request, "biciapp/panel_administracion.html", contexto)


def cerrar_sesion(request):
    if request.method == "POST":
        logout(request)
        messages.success(request, "Cerraste sesión correctamente.")
    return redirect("inicio")
