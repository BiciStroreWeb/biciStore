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
