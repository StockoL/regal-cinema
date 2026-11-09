import threading
import time
from datetime import timedelta

from django.db import IntegrityError, connection, transaction
from django.test import TransactionTestCase
from django.utils import timezone

from bookings.models import SeatHold
from bookings.services import SeatsUnavailable, hold_seats
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

    def test_hold_seats_names_a_seat_lost_after_its_check(self):
        """Forces the race inside hold_seats: the other customer's hold
        isn't committed when the check runs, so the check passes, and
        the insert then waits on the database and loses. The customer
        is told which seat went and nothing of theirs is held."""
        screening, (seat_1, seat_2) = make_screening()
        adult = TicketType.objects.get(name='Adult')
        inserted = threading.Event()
        outcome = {}

        def other_customer_holds_seat_2():
            try:
                with transaction.atomic():
                    SeatHold.objects.create(
                        screening=screening, seat=seat_2, ticket_type=adult,
                        session_key='session-b',
                        expires_at=timezone.now() + timedelta(minutes=10),
                    )
                    inserted.set()
                    # Still uncommitted while this customer checks.
                    time.sleep(1)
            finally:
                connection.close()

        def this_customer_holds_both():
            try:
                inserted.wait(timeout=10)
                hold_seats(screening, [(seat_1, adult), (seat_2, adult)],
                           'session-a')
                outcome['result'] = 'held'
            except SeatsUnavailable as error:
                outcome['result'] = error.seats
            finally:
                connection.close()

        threads = [threading.Thread(target=other_customer_holds_seat_2),
                   threading.Thread(target=this_customer_holds_both)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)

        self.assertEqual(outcome['result'], [seat_2])
        self.assertEqual(
            list(SeatHold.objects.values_list('session_key', flat=True)),
            ['session-b'],
        )
