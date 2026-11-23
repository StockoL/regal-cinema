from django.core.management.base import BaseCommand

from bookings.reconcile import recheck_stuck_payments


class Command(BaseCommand):
    help = (
        'Ask Stripe about pending bookings whose webhook never came '
        '(architecture 4.32). Safe to run twice.'
    )

    def handle(self, *args, **options):
        counts = recheck_stuck_payments()
        payments = 'payment' if counts['checked'] == 1 else 'payments'
        self.stdout.write(
            f"Checked {counts['checked']} stuck {payments}: "
            f"{counts['paid']} paid, {counts['unreachable']} unreachable."
        )
