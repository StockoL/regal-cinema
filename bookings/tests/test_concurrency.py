import threading
from datetime import timedelta

from django.db import IntegrityError, connection, transaction
from django.test import TransactionTestCase
from django.utils import timezone

from bookings.models import SeatHold
from bookings.tests.test_holds import make_screening
from screenings.models import TicketType


class ConcurrentHoldTests(TransactionTestCase):
    """The double-booking spike (build plan, before any seat code). Two
    customers try to hold the same seat at the same instant, each on its
    own database connection, so the only thing that can stop both
    succeeding is the database. This is why the project never runs on
    SQLite (development log, 24 October).

    A TransactionTestCase, because each thread must see the other's
    committed rows. serialized_rollback puts back the ticket types the
    migrations seeded, which the flush afterwards would otherwise wipe.
    """

    serialized_rollback = True

    def test_only_one_of_two_simultaneous_holds_succeeds(self):
        screening, (seat, _) = make_screening()
        adult = TicketType.objects.get(name='Adult')
        start = threading.Barrier(2)
        results = []

        def try_to_hold(session_key):
            try:
                start.wait()
                with transaction.atomic():
                    SeatHold.objects.create(
                        screening=screening, seat=seat, ticket_type=adult,
                        session_key=session_key,
                        expires_at=timezone.now() + timedelta(minutes=10),
                    )
                results.append('held')
            except IntegrityError:
                results.append('refused')
            finally:
                connection.close()

        threads = [
            threading.Thread(target=try_to_hold, args=(key,))
            for key in ('session-a', 'session-b')
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)

        self.assertCountEqual(results, ['held', 'refused'])
        self.assertEqual(SeatHold.objects.count(), 1)
