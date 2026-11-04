import django.db.models.deletion
from django.db import migrations, models


def give_existing_screenings_a_layout(apps, schema_editor):
    """Each screen that already has screenings gets a Standard layout,
    made the default, and its screenings use it."""
    Screen = apps.get_model('screenings', 'Screen')
    SeatingLayout = apps.get_model('screenings', 'SeatingLayout')
    for screen in Screen.objects.filter(screenings__isnull=False).distinct():
        layout = screen.layouts.filter(is_default=True).first()
        if layout is None:
            layout, _ = screen.layouts.get_or_create(
                name='Standard',
                defaults={'is_default': not screen.layouts.exists()},
            )
        screen.screenings.filter(layout__isnull=True).update(layout=layout)


class Migration(migrations.Migration):

    dependencies = [
        ('screenings', '0012_seat_uniqueness'),
    ]

    operations = [
        migrations.AddField(
            model_name='screening',
            name='layout',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='screenings', to='screenings.seatinglayout',
            ),
        ),
        migrations.RunPython(
            give_existing_screenings_a_layout, migrations.RunPython.noop
        ),
        migrations.AlterField(
            model_name='screening',
            name='layout',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='screenings', to='screenings.seatinglayout',
            ),
        ),
    ]
