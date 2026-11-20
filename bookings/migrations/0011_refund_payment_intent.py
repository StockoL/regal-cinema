from django.db import migrations, models


def copy_from_booking(apps, schema_editor):
    Refund = apps.get_model('bookings', 'Refund')
    for refund in Refund.objects.select_related('booking'):
        refund.stripe_payment_intent_id = (
            refund.booking.stripe_payment_intent_id or ''
        )
        refund.save(update_fields=['stripe_payment_intent_id'])


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0010_refund'),
    ]

    operations = [
        migrations.AddField(
            model_name='refund',
            name='stripe_payment_intent_id',
            field=models.CharField(default='', max_length=255),
            preserve_default=False,
        ),
        migrations.RunPython(copy_from_booking, migrations.RunPython.noop),
    ]
