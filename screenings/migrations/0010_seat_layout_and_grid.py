import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('screenings', '0009_seat_constraint_after_rename'),
    ]

    operations = [
        migrations.AddField(
            model_name='seat',
            name='layout',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='seats', to='screenings.seatinglayout',
            ),
        ),
        # Existing seats get a position of 0, 0 and are placed properly
        # when the seat plans are seeded.
        migrations.AddField(
            model_name='seat',
            name='row_index',
            field=models.PositiveSmallIntegerField(default=0),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='seat',
            name='column_index',
            field=models.PositiveSmallIntegerField(default=0),
            preserve_default=False,
        ),
    ]
