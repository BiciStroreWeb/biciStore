from django.db import migrations, models


RESEÑAS_INICIALES = [
    (5, "Compré la Trek Marlin 7 Gen 3 para empezar a hacer recorridos por montaña y hasta ahora me ha gustado mucho. La bicicleta se siente bastante estable y la suspensión funciona muy bien cuando paso por caminos con piedras.", "Carlos M.", "Trek Marlin 7 Gen 3"),
    (5, "La Specialized Rockhopper fue una muy buena elección. La uso principalmente los fines de semana y también para salir a pasear con mis amigos. Es cómoda y hasta ahora no he tenido ningún problema.", "Andrea R.", "Specialized Rockhopper"),
    (4, "Me decidí por la Giant Contend AR 1 porque quería una bicicleta para empezar a entrenar en carretera. Me ha sorprendido lo cómoda que es en recorridos largos y el cambio de velocidades funciona bastante bien.", "Miguel A.", "Giant Contend AR 1"),
    (5, "Uso la Cannondale Quick 4 prácticamente todos los días para ir al trabajo. Me gusta porque es ligera y fácil de manejar en la ciudad. También me ha resultado muy cómoda para hacer recorridos más largos.", "Sofía L.", "Cannondale Quick 4"),
    (5, "Después de comparar varios modelos elegí la Trek Domane AL 2. La he utilizado para recorridos de más de 50 kilómetros y me ha parecido muy cómoda. El diseño también me gustó bastante.", "Daniel P.", "Trek Domane AL 2 Gen 4"),
    (4, "La Cannondale Trail 5 me ha funcionado muy bien para comenzar a salir a caminos de tierra. Me gusta que las llantas dan bastante seguridad y los frenos responden bien cuando voy bajando.", "Fernando G.", "Cannondale Trail 5"),
    (5, "Es mi primera bicicleta de montaña y estoy muy contenta con la compra. Al principio no sabía qué modelo elegir, pero después de revisar las características encontré una que se ajustaba a lo que estaba buscando.", "Mariana T.", "Bicicleta de montaña"),
    (5, "Me gustó mucho la experiencia. La bicicleta llegó en buenas condiciones y el diseño está muy bonito. La he usado varias veces para salir los domingos y funciona exactamente como esperaba.", "Luis R.", "Bicicleta urbana"),
]


def cargar_resenas_iniciales(apps, schema_editor):
    Resena = apps.get_model("biciapp", "Resena")
    Resena.objects.bulk_create(
        [
            Resena(estrellas=estrellas, texto=texto, autor=autor, compra=compra)
            for estrellas, texto, autor, compra in RESEÑAS_INICIALES
        ]
    )


class Migration(migrations.Migration):
    dependencies = [("biciapp", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="Resena",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("estrellas", models.PositiveSmallIntegerField(default=5)),
                ("texto", models.TextField()),
                ("autor", models.CharField(default="Cliente", max_length=100)),
                ("compra", models.CharField(blank=True, max_length=150)),
                ("creada_en", models.DateTimeField(auto_now_add=True)),
                ("actualizada_en", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "reseña",
                "verbose_name_plural": "reseñas",
                "ordering": ["-creada_en", "-id"],
            },
        ),
        migrations.RunPython(cargar_resenas_iniciales, migrations.RunPython.noop),
    ]
