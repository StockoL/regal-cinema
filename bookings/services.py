from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone

from .basket import check_basket
from .models import Booking, SeatHold


class SeatsUnavailable(Exception):
    """Some chosen seats can't be held: taken by someone else, closed
    for this screening, or out of use. Names them, so the page can mark
    just those and keep the customer's other choices (4.8 step 4)."""

    def __init__(self, seats):
        super().__init__(f'{len(seats)} seat(s) unavailable')
        self.seats = seats


# The longest a customer can keep seats in total, however often they
# amend. Fixed, not a venue setting: it matches the shortest session
# Stripe Checkout allows, so the one extension at Pay always covers a
# whole session (4.8, 4.23).
HOLD_CAP_MINUTES = 30


class HoldTimeUsedUp(Exception):
    """The booking has had its 30 minutes, so the customer chooses
    their seats again from the start."""


def check_ticket_types(screening, choices):
    offered = set(screening.film.ticket_types())
    if any(ticket_type not in offered for _, ticket_type in choices):
        raise ValueError("A ticket type isn't offered for this film.")


def hold_seats(screening, choices, session_key, user=None, expires_at=None):
    """Hold every chosen seat with its ticket type, or none of them
    (architecture 4.8 step 3). choices is a list of (seat, ticket_type).

    Shared by the online flow and the staff till (4.14), so the online
    sales cut-off is checked by the online flow before calling this.
    The database constraint is the final word if two customers race for
    a seat between the check and the insert.
    """
    check_ticket_types(screening, choices)

    with transaction.atomic():
        now = timezone.now()
        screening.holds.filter(expires_at__lte=now).delete()
        available = set(screening.seats())
        held = set(screening.holds.values_list('seat', flat=True))
        unavailable = [
            seat for seat, _ in choices
            if seat not in available or seat.pk in held
        ]
        if unavailable:
            raise SeatsUnavailable(unavailable)
        if expires_at is None:
            expires_at = now + timedelta(minutes=settings.SEAT_HOLD_MINUTES)
        try:
            with transaction.atomic():
                return SeatHold.objects.bulk_create([
                    SeatHold(
                        screening=screening, seat=seat,
                        ticket_type=ticket_type, session_key=session_key,
                        user=user, expires_at=expires_at,
                    )
                    for seat, ticket_type in choices
                ])
        except IntegrityError:
            # Someone held one of these seats in the moment since the
            # check. Name whichever are now taken.
            taken = set(screening.holds.values_list('seat', flat=True))
            raise SeatsUnavailable(
                [seat for seat, _ in choices if seat.pk in taken]
            ) from None


def start_booking(screening, choices, infants, session_key, user=None):
    """Proceed to checkout: check the basket, hold the seats and make
    the pending booking that holds everything else, in one transaction,
    so a refusal at any step leaves nothing behind (4.2, 4.8 step 3).
    Raises BasketError or SeatsUnavailable."""
    check_basket(
        screening.film, [ticket_type for _, ticket_type in choices], infants
    )
    with transaction.atomic():
        holds = hold_seats(screening, choices, session_key, user=user)
        booking = Booking.objects.create(
            screening=screening, user=user, infant_count=infants,
        )
        SeatHold.objects.filter(pk__in=[hold.pk for hold in holds]).update(
            booking=booking
        )
    return booking


def seat_plan(screening, own_booking=None):
    """The seats a customer can see for a screening, grouped as they'd
    look for them: the stalls (or each table), then each circle row.
    Each seat has a status: available, sold (held by anyone or sold),
    or outside section (an area closed for this screening, 4.1, 4.17).
    The customer's own held seats count as available to them. Seats out
    of use and other layouts' seats aren't shown."""
    seats = screening.screen.seats.filter(
        Q(layout__isnull=True) | Q(layout=screening.layout_id),
        is_active=True,
    ).order_by('-area', 'row_index', 'column_index')
    closed = set(screening.closed_areas.values_list('area', flat=True))
    held = screening.holds.live()
    if own_booking is not None:
        held = held.exclude(booking=own_booking)
    held = set(held.values_list('seat', flat=True))
    groups = {}
    for seat in seats:
        if seat.area in closed:
            status = 'outside section'
        elif seat.pk in held:
            status = 'sold'
        else:
            status = 'available'
        groups.setdefault(group_label(seat), []).append((seat, status))
    return list(groups.items())


def group_label(seat):
    if seat.area == seat.Area.CIRCLE:
        return f'Circle, row {seat.row_label}'
    if seat.table_number:
        return f'Stalls, table {seat.table_number}'
    return 'Stalls'


def amend_booking(booking, choices, infants, session_key, user=None):
    """Change a pending booking's seats, ticket types or infants without
    starting again (4.8 step 11). In one transaction, seats no longer
    wanted are released, new ones held and kept ones given their new
    ticket type, so the customer never holds nothing or both. Each
    change restarts the timer, but never past 30 minutes from when the
    booking started. Raises BasketError, SeatsUnavailable or
    HoldTimeUsedUp, and leaves the booking as it was if it does."""
    check_basket(
        booking.screening.film,
        [ticket_type for _, ticket_type in choices], infants,
    )
    check_ticket_types(booking.screening, choices)
    now = timezone.now()
    cap = booking.created_at + timedelta(minutes=HOLD_CAP_MINUTES)
    if now >= cap:
        raise HoldTimeUsedUp()
    expires_at = min(
        now + timedelta(minutes=settings.SEAT_HOLD_MINUTES), cap
    )
    wanted = {seat.pk: ticket_type for seat, ticket_type in choices}

    with transaction.atomic():
        Booking.objects.select_for_update().get(pk=booking.pk)
        booking.holds.exclude(seat__in=list(wanted)).delete()
        # A hold of theirs that ran out is held again like a new seat,
        # in case someone else has it now.
        booking.holds.filter(expires_at__lte=now).delete()
        kept = list(booking.holds.all())
        for hold in kept:
            hold.ticket_type = wanted[hold.seat_id]
            hold.expires_at = expires_at
            hold.save(update_fields=['ticket_type', 'expires_at'])
        kept_seats = {hold.seat_id for hold in kept}
        added = [(seat, ticket_type) for seat, ticket_type in choices
                 if seat.pk not in kept_seats]
        if added:
            holds = hold_seats(booking.screening, added, session_key,
                               user=user, expires_at=expires_at)
            SeatHold.objects.filter(
                pk__in=[hold.pk for hold in holds]
            ).update(booking=booking)
        booking.infant_count = infants
        booking.save(update_fields=['infant_count'])
    return booking


def cancel_pending_booking(booking):
    """Let a pending booking's seats go at once rather than waiting for
    the holds to run out. Nothing was charged, so the booking is deleted
    and its holds with it (4.2, 4.8 step 6)."""
    if booking.status != booking.Status.PENDING:
        raise ValueError('Only a pending booking can be let go like this.')
    booking.delete()
