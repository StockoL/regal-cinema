import hashlib
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone

from accounts.models import get_system_user
from payments import get_provider
from payments.base import FeeUnavailable, RefundFailed
from screenings.models import Seat
from screenings.services import layout_seats
from venue.models import get_settings

from .basket import check_basket
from .emails import queue_booking_confirmation, queue_late_payment_refund
from .models import Booking, Refund, SeatBooking, SeatHold


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
        held |= set(
            screening.seat_bookings.live().values_list('seat', flat=True)
        )
        unavailable = [
            seat for seat, _ in choices
            if seat not in available or seat.pk in held
        ]
        if unavailable:
            raise SeatsUnavailable(unavailable)
        if expires_at is None:
            expires_at = now + timedelta(
                minutes=get_settings().seat_hold_minutes
            )
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
            seat_count=len(choices),
        )
        SeatHold.objects.filter(pk__in=[hold.pk for hold in holds]).update(
            booking=booking
        )
    return booking


class SeatsLost(Exception):
    """Another sale took one of the booking's seats, so none of them
    were sold. Once payments arrive, this is the automatic refund path
    (4.13)."""


def confirm_booking(booking):
    """Everything that happens together when a booking is paid, in one
    transaction: its holds become SeatBooking rows at this screening's
    prices, with the VAT rate snapshotted, and the booking is marked
    paid. Calling it again for a paid booking changes nothing (4.32).
    Raises SeatsLost, and saves nothing, if any seat has gone."""
    with transaction.atomic():
        booking = Booking.objects.select_for_update().get(pk=booking.pk)
        if booking.status != Booking.Status.PENDING:
            return booking
        prices = {price.ticket_type_id: price.price_pence
                  for price in booking.screening.prices.all()}
        holds = list(booking.holds.select_related('ticket_type'))
        if len(holds) != booking.seat_count:
            raise SeatsLost()
        try:
            with transaction.atomic():
                SeatBooking.objects.bulk_create([
                    SeatBooking(
                        booking=booking, screening=booking.screening,
                        seat=hold.seat, ticket_type=hold.ticket_type,
                        price_pence=prices[hold.ticket_type_id],
                        vat_rate_percent=hold.ticket_type.vat_rate_percent,
                    )
                    for hold in holds
                ])
        except IntegrityError:
            raise SeatsLost() from None
        booking.holds.all().delete()
        booking.status = Booking.Status.PAID
        booking.paid_at = timezone.now()
        booking.save(update_fields=['status', 'paid_at'])
        queue_booking_confirmation(booking)
    return booking


def record_payment_fee(booking_pk):
    """Store what Stripe kept from a paid booking and what reached the
    venue. Run after the booking is confirmed and committed, so if the
    lookup fails the booking still stands and the fee is filled in by a
    later try (4.13)."""
    booking = Booking.objects.get(pk=booking_pk)
    try:
        fee = get_provider().payment_fee(booking.stripe_payment_intent_id)
    except FeeUnavailable:
        return
    booking.stripe_fee_pence = fee.fee_pence
    booking.stripe_net_pence = fee.net_pence
    booking.save(update_fields=['stripe_fee_pence', 'stripe_net_pence'])


def refund_late_payment(booking):
    """A payment arrived after the booking's seats were sold to someone
    else (4.13). The booking is marked refunded and what was charged is
    refunded, so the customer is never left paying for seats they don't
    have."""
    booking.holds.all().delete()
    booking.status = Booking.Status.REFUNDED
    booking.save(update_fields=['status'])
    queue_late_payment_refund(booking)
    return queue_refund(
        booking, booking.stripe_payment_intent_id,
        booking.amount_charged_pence,
        'Paid after the seats were sold to someone else',
    )


def refund_duplicate_payment(booking, payment_intent_id, amount_pence):
    """A second payment arrived for a booking already settled, such as
    a customer paying on two sessions (4.32, "Paying twice"). It's
    refunded against itself and the booking is left as it was."""
    return queue_refund(booking, payment_intent_id, amount_pence,
                        'duplicate_payment')


def queue_refund(booking, payment_intent_id, amount_pence, reason):
    """Record a pending refund, named to the system user, and send it to
    the provider once the transaction has committed (4.13)."""
    refund = Refund.objects.create(
        booking=booking, stripe_payment_intent_id=payment_intent_id,
        amount_pence=amount_pence, reason=reason,
        created_by=get_system_user(),
    )
    transaction.on_commit(lambda: send_refund(refund.pk))
    return refund


def send_refund(refund_pk):
    """Ask the provider for a pending refund and record the answer. The
    idempotency key comes from the refund's row, so sending it again,
    as a retry does, can never pay out twice (4.13, 4.32)."""
    refund = Refund.objects.get(pk=refund_pk)
    try:
        refund.stripe_refund_id = get_provider().refund(
            payment_intent_id=refund.stripe_payment_intent_id,
            amount_pence=refund.amount_pence,
            idempotency_key=f'refund-{refund.pk}',
        )
        refund.status = Refund.Status.SUCCEEDED
    except RefundFailed as error:
        refund.status = Refund.Status.FAILED
        refund.error = str(error)
    refund.save(update_fields=['stripe_refund_id', 'status', 'error'])


def release_seats(booking):
    """Put a booking's sold seats back on sale at once. The rows are
    kept with released_at set, never deleted, so the sale stays on
    record (4.2, 4.8). Seats already released keep their first time."""
    booking.seats.live().update(released_at=timezone.now())


def basket_total(booking, holds):
    """What the customer pays for their held seats, in pence, at this
    screening's prices. Food, discounts and vouchers join it as those
    features arrive (4.10)."""
    prices = {price.ticket_type_id: price.price_pence
              for price in booking.screening.prices.all()}
    return sum(prices[hold.ticket_type_id] for hold in holds)


class HoldsExpired(Exception):
    """Some of the booking's seats are no longer held, so the customer
    has to choose them again before paying."""


# Stripe refuses a session that expires less than 30 minutes after it
# receives the request, so the session asks for a minute more (4.13).
CHECKOUT_SESSION_MINUTES = 31


def start_payment(booking, success_url, cancel_url):
    """The customer chose Pay (4.13 step 3). Ask the payment provider
    for a Checkout Session for the total, store its id on the booking,
    and extend the holds once to the session's expiry, so the seats
    can't go to anyone else while the customer pays (4.8 step 5). The
    idempotency key comes from the booking and its basket, so pressing
    Pay twice gets the same session. Raises HoldsExpired."""
    holds = list(booking.holds.live().select_related('ticket_type'))
    if len(holds) != booking.seat_count:
        raise HoldsExpired()
    total = basket_total(booking, holds)
    provider = get_provider()
    previous = booking.stripe_checkout_session_id
    if previous:
        # Back while the session is still open: return to it (4.13 step
        # 7). Confirming sells whatever is held, so only the total has
        # to match.
        current = provider.get_checkout_session(previous)
        if current.is_open and current.amount_pence == total:
            return current
    # The previous session is part of the key, so a session that expired
    # or closed is followed by a new one, not handed back by Stripe.
    basket = sorted((hold.seat_id, hold.ticket_type_id) for hold in holds)
    key = hashlib.sha256(
        f'{booking.pk}:{basket}:{booking.infant_count}:{total}:{previous}'
        .encode()
    ).hexdigest()
    tickets = 'ticket' if len(holds) == 1 else 'tickets'
    session = provider.create_checkout_session(
        reference=booking.reference, amount_pence=total,
        description=f'{booking.screening.film.title}, '
                    f'{len(holds)} {tickets}',
        success_url=success_url, cancel_url=cancel_url,
        expires_at=timezone.now() + timedelta(
            minutes=CHECKOUT_SESSION_MINUTES
        ),
        idempotency_key=f'checkout-{key}',
    )
    with transaction.atomic():
        booking.stripe_checkout_session_id = session.id
        booking.save(update_fields=['stripe_checkout_session_id'])
        booking.holds.update(expires_at=session.expires_at)
    return session


def seat_plan(screening, own_booking=None):
    """The seats a customer can see for a screening, area by area (the
    stalls, then the circle), each with how many grid columns it spans.
    Each seat has a status: available, sold (held by anyone else or
    sold) or outside section (an area closed for this screening, 4.1,
    4.17). The customer's own held seats count as available to them.
    Seats out of use and other layouts' seats aren't shown, so they
    leave a gap in the grid."""
    seats = layout_seats(screening.screen_id, screening.layout_id)
    closed = set(screening.closed_areas.values_list('area', flat=True))
    held = screening.holds.live()
    if own_booking is not None:
        held = held.exclude(booking=own_booking)
    held = set(held.values_list('seat', flat=True))
    held |= set(
        screening.seat_bookings.live().values_list('seat', flat=True)
    )
    areas = []
    for area, name in ((Seat.Area.STALLS, 'Stalls'),
                       (Seat.Area.CIRCLE, 'Circle')):
        in_area = [seat for seat in seats if seat.area == area]
        if not in_area:
            continue
        # Lettered rows (the circle) get their letter in the first grid
        # column, so their seats move over by one.
        rows = sorted({(seat.row_index + 1, seat.row_label)
                       for seat in in_area
                       if seat.row_label and not seat.label_override})
        first_col = 2 if rows else 1
        areas.append({
            'name': name,
            'columns': max(seat.column_index for seat in in_area) + first_col,
            'first_col': first_col,
            'rows': rows,
            'seats': [(seat, seat_status(seat, closed, held))
                      for seat in in_area],
        })
    return areas


def seat_status(seat, closed_areas, held_seats):
    if seat.area in closed_areas:
        return 'outside section'
    if seat.pk in held_seats:
        return 'sold'
    return 'available'


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
        now + timedelta(minutes=get_settings().seat_hold_minutes), cap
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
        booking.seat_count = len(choices)
        booking.save(update_fields=['infant_count', 'seat_count'])
    return booking


def cancel_pending_booking(booking):
    """Let a pending booking's seats go at once rather than waiting for
    the holds to run out. Nothing was charged, so the booking is deleted
    and its holds with it (4.2, 4.8 step 6)."""
    if booking.status != booking.Status.PENDING:
        raise ValueError('Only a pending booking can be let go like this.')
    booking.delete()
