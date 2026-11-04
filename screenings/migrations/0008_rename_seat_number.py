from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('screenings', '0007_seatinglayout'),
    ]

    operations = [
        migrations.RenameField(
            model_name='seat',
            old_name='seat_number',
            new_name='number',
        ),
    ]
