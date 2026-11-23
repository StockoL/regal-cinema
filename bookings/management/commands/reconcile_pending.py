from django.core.management.base import BaseCommand

from bookings.reconcile import (
    recheck_stuck_payments,
    retry_emails,
    retry_fees,
    retry_refunds,
    tidy_up,
)


class Command(BaseCommand):
    help = (
        'Ask Stripe about pending bookings whose webhook never came, '
        'send failed refunds and emails again, fill in missing fees, '
        'then clear away old holds and abandoned bookings (architecture '
        '4.32). Safe to run twice.'
    )

    def handle(self, *args, **options):
        counts = recheck_stuck_payments()
        payments = 'payment' if counts['checked'] == 1 else 'payments'
        self.stdout.write(
            f"Checked {counts['checked']} stuck {payments}: "
            f"{counts['paid']} paid, {counts['unreachable']} unreachable."
        )
        refunds = retry_refunds()
        noun = 'refund' if refunds['retried'] == 1 else 'refunds'
        self.stdout.write(
            f"Retried {refunds['retried']} {noun}: "
            f"{refunds['succeeded']} succeeded."
        )
        emails = retry_emails()
        noun = 'email' if emails['retried'] == 1 else 'emails'
        self.stdout.write(
            f"Retried {emails['retried']} {noun}: {emails['sent']} sent."
        )
        fees = retry_fees()
        noun = 'fee' if fees['retried'] == 1 else 'fees'
        self.stdout.write(
            f"Looked up {fees['retried']} missing {noun}: "
            f"{fees['filled']} filled in."
        )
        removed = tidy_up()
        holds = 'hold' if removed['holds'] == 1 else 'holds'
        bookings = 'booking' if removed['bookings'] == 1 else 'bookings'
        self.stdout.write(
            f"Removed {removed['holds']} expired {holds} and "
            f"{removed['bookings']} abandoned {bookings}."
        )
