# Carrito y checkout simulado de BiciStore

Se agregó un carrito basado en sesión, botones **Comprar**, actualización y eliminación de productos, un checkout simulado y un correo de confirmación.

## Seguridad

- Los datos de tarjeta sólo se validan durante la solicitud.
- El número de tarjeta, vencimiento y CVV nunca se guardan en la base de datos, sesión ni correo.
- No se realiza ningún cargo real.
- En el formulario se usan `inputmode`, `pattern`, `maxlength` y validación adicional en el servidor.

## Correo

Por defecto Django usa `console.EmailBackend`, así que durante desarrollo el correo aparece en la terminal donde se ejecuta `runserver`.

Para SMTP real, define estas variables de entorno antes de ejecutar Django:

```bash
export EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
export EMAIL_HOST=smtp.example.com
export EMAIL_PORT=587
export EMAIL_HOST_USER=tu-cuenta@example.com
export EMAIL_HOST_PASSWORD=tu-contraseña-o-app-password
export EMAIL_USE_TLS=1
export DEFAULT_FROM_EMAIL=tu-cuenta@example.com
```

Después inicia el servidor con `python manage.py runserver`. Se envía un correo al email indicado por el comprador con el nombre, folio, bicicletas y total.
