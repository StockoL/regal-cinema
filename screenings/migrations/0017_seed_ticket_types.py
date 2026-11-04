from django.db import migrations

# Architecture 4.1. Reference data every deployment needs, so it comes
# from a migration rather than a command run by hand.
TICKET_TYPES = [
    {'name': 'Adult', 'description': ''},
    {'name': 'Student', 'requires_proof': True,
     'description': 'Over 18, in full-time education. Bring your '
                    'student card.'},
    {'name': 'OAP', 'requires_proof': True,
     'description': 'For pensioners. Bring proof of age.'},
    {'name': 'Young person', 'max_age': 17,
     'description': 'Aged 12 to 17.'},
    {'name': 'Child', 'requires_adult': True, 'max_age': 11,
     'description': 'Aged 2 to 11. Must come with an adult.'},
    {'name': 'Companion', 'requires_proof': True, 'is_companion': True,
     'description': 'Free, for someone accompanying a CEA Card holder. '
                    'Bring the CEA Card.'},
]


def seed_ticket_types(apps, schema_editor):
    """Create the six types, or bring an existing one of the same name
    up to date, so a database that already has some isn't duplicated."""
    TicketType = apps.get_model('screenings', 'TicketType')
    for fields in TICKET_TYPES:
        defaults = {
            'requires_adult': False, 'requires_proof': False,
            'is_companion': False, 'max_age': None, **fields,
        }
        TicketType.objects.update_or_create(
            name=defaults.pop('name'), defaults=defaults,
        )


class Migration(migrations.Migration):

    dependencies = [
        ('screenings', '0016_tickettype_rules'),
    ]

    operations = [
        # Left in place on reverse: the types may already be on bookings.
        migrations.RunPython(seed_ticket_types, migrations.RunPython.noop),
    ]
