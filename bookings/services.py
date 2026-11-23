import hashlib
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone

from accounts.models import get_system_user
from membership.models import Voucher
from payments import get_provider
from payments.base import FeeUnavailable, RefundFailed
from screenings.models import Seat
from screenings.services import layout_seats
from staff.audit import log_action
from staff.models import AuditLogEntry
from venue.models import get_settings

from .basket import check_basket
from .emails import (
    queue_booking_confirmation,
    queue_cancellation_approved,
    queue_cancellation_declined,
    queue_late_payment_refund,
)
from .models import (
    REFERENCE_CHARACTERS,
    Booking,
    Cancellation,
    Refund,
    SeatBooking,
    SeatHold,
)


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
        screening.film, [ticket_type for _, ticket_type in choices], infants,
        max_tickets=get_settings().max_tickets_per_booking,
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


def settle_payment(booking, payment_intent_id, amount_pence):
    """Act on Stripe's word that a booking's session was paid, whether
    it came by webhook or by asking Stripe (4.32). A pending booking is
    confirmed, or refunded if its seats have gone. A settled booking
    paid again by a different payment has that payment refunded. The
    booking is locked first, so two reports of one payment act once."""
    with transaction.atomic():
        booking = Booking.objects.select_for_update().get(pk=booking.pk)
        if booking.status != Booking.Status.PENDING:
            if payment_intent_id != booking.stripe_payment_intent_id:
                refund_duplicate_payment(booking, payment_intent_id,
                                         amount_pence)
            return
        # Recorded before confirming, so a refund can find the payment
        # even if the seats turn out to be lost.
        booking.stripe_payment_intent_id = payment_intent_id
        booking.amount_charged_pence = amount_pence
        booking.save(update_fields=['stripe_payment_intent_id',
                                    'amount_charged_pence'])
        try:
            confirm_booking(booking)
        except SeatsLost:
            refund_late_payment(booking)
        else:
            transaction.on_commit(lambda: record_payment_fee(booking.pk))


def recheck_payment(booking):
    """Ask Stripe whether the booking's session was paid, for when its
    webhook never came (4.32). A paid session is settled just as the
    webhook would settle it, so running this alongside the webhook acts
    once. Returns whether Stripe said it was paid."""
    if not booking.stripe_checkout_session_id:
        return False
    session = get_provider().get_checkout_session(
        booking.stripe_checkout_session_id
    )
    if not session.paid:
        return False
    settle_payment(booking, session.payment_intent_id, session.amount_pence)
    return True


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


class CancellationNotAllowed(Exception):
    """The booking can't be cancelled online now: it isn't paid, it has
    already been asked about, it's past, or it's inside the cutoff."""


def cancellation_state(booking, venue=None):
    """What a customer can do about cancelling a booking (4.22).

    'open' when it's paid and more than the venue's cutoff away, so the
    request form is offered; 'phone' when it's paid but inside the
    cutoff and still to come, so the page gives the box office; None
    for a booking that's past, not paid or already being dealt with.
    A page listing many bookings passes the venue settings in, so they
    are read once.
    """
    if booking.status != Booking.Status.PAID:
        return None
    starts = booking.screening.date_time
    now = timezone.now()
    if starts <= now:
        return None
    venue = venue or get_settings()
    cutoff = timedelta(hours=venue.cancellation_cutoff_hours)
    return 'open' if now < starts - cutoff else 'phone'


def request_cancellation(booking, reason=''):
    """A customer asks to cancel a booking (4.22). A Cancellation is
    recorded with their reason and the booking moves to
    cancellation_requested, for staff to approve or decline. Raises
    CancellationNotAllowed if it can't be asked for online."""
    with transaction.atomic():
        booking = Booking.objects.select_for_update().select_related(
            'screening'
        ).get(pk=booking.pk)
        if cancellation_state(booking) != 'open':
            raise CancellationNotAllowed()
        cancellation = Cancellation.objects.create(
            booking=booking, kind=Cancellation.Kind.CUSTOMER_REQUEST,
            reason=reason,
        )
        booking.status = Booking.Status.CANCELLATION_REQUESTED
        booking.save(update_fields=['status'])
    return cancellation


def decide(cancellation, staff, note, status):
    """Lock a waiting request and its booking, and record the decision
    on the request. Shared by approving and declining, which each need
    a note (4.22). Raises ValueError without a note, and
    CancellationNotAllowed if the request isn't waiting."""
    if not note or not note.strip():
        raise ValueError('A decision needs a note to the customer.')
    cancellation = Cancellation.objects.select_for_update().get(
        pk=cancellation.pk
    )
    if cancellation.status != Cancellation.Status.REQUESTED:
        raise CancellationNotAllowed()
    # Lock the booking alone: its customer is an optional join.
    cancellation.booking = (
        Booking.objects.select_for_update(of=('self',))
        .select_related('screening__film', 'user')
        .get(pk=cancellation.booking_id)
    )
    cancellation.status = status
    cancellation.decided_by = staff
    cancellation.decided_at = timezone.now()
    cancellation.decision_note = note.strip()
    return cancellation


def decline_cancellation(cancellation, staff, note):
    """Staff turn a customer's request down (4.22). The note goes to the
    customer. The booking returns to paid, the decision is logged with
    the staff member's name, and the customer can ask again later."""
    with transaction.atomic():
        cancellation = decide(cancellation, staff, note,
                              Cancellation.Status.DECLINED)
        cancellation.save()
        booking = cancellation.booking
        booking.status = Booking.Status.PAID
        booking.save(update_fields=['status'])
        log_action(staff, AuditLogEntry.Action.CANCELLATION_DECLINED,
                   note, booking=booking)
        queue_cancellation_declined(booking, cancellation.decision_note)
    return cancellation


def booking_value(booking):
    """What a booking was worth to the customer: what was charged, or,
    for one marked paid by hand, its seats' stored prices. Never worked
    out again from today's prices (4.2)."""
    if booking.amount_charged_pence is not None:
        return booking.amount_charged_pence
    return sum(booking.seats.values_list('price_pence', flat=True))


def approve_cancellation(cancellation, staff, note):
    """Staff agree to a customer's request (4.22). The customer gets a
    voucher for the booking's value less the venue's cancellation fee,
    the seats go back on sale at once, the booking is cancelled, and the
    decision is logged with the voucher. The customer is emailed the
    code."""
    with transaction.atomic():
        cancellation = decide(cancellation, staff, note,
                              Cancellation.Status.APPROVED)
        booking = cancellation.booking
        fee = get_settings().cancellation_fee_pence
        value = max(booking_value(booking) - fee, 0)
        voucher = Voucher.objects.create(
            initial_value_pence=value, remaining_value_pence=value,
            source=Voucher.Source.BOOKING_CANCELLED, source_booking=booking,
        )
        cancellation.outcome = Cancellation.Outcome.VOUCHER
        cancellation.fee_pence = fee
        cancellation.save()
        release_seats(booking)
        booking.status = Booking.Status.CANCELLED
        booking.save(update_fields=['status'])
        log_action(staff, AuditLogEntry.Action.BOOKING_CANCELLED, note,
                   booking=booking, voucher=voucher)
        queue_cancellation_approved(cancellation, voucher)
    return cancellation


def reference_code(query):
    """What staff typed, as the five characters after RGL-: any case,
    with spaces or a hyphen, with or without the RGL."""
    code = query.strip().upper().replace(' ', '').replace('-', '')
    return code[3:] if code.startswith('RGL') else code


def impossible_reference(query):
    """Whether what was typed is shaped like a reference but holds a
    character references never have (0, O, 1, I or L, see 4.2), so the
    page can say why nothing was found. An email address is left
    alone, since it often has an l in it."""
    code = reference_code(query)
    return ('@' not in query and len(code) == 5 and code.isalnum()
            and any(c not in REFERENCE_CHARACTERS for c in code))


def find_bookings(query, on_date=None):
    """The staff search box (4.32): a booking reference however it was
    typed, in any case, with spaces, without its hyphen or its RGL, or
    part of the customer's email address. A date narrows it to that
    day's screenings. Bookings still at checkout aren't found."""
    query = query.strip()
    if not query:
        return Booking.objects.none()
    code = reference_code(query)
    matches = Q(user__email__icontains=query)
    if len(code) == 5:
        matches |= Q(reference=f'RGL-{code}')
    bookings = Booking.objects.filter(matches).exclude(
        status=Booking.Status.PENDING
    )
    if on_date is not None:
        bookings = bookings.filter(screening__date_time__date=on_date)
    return (bookings.select_related('screening__film', 'screening__screen',
                                    'user', 'checked_in_by')
            .order_by('screening__date_time'))


class CheckInRefused(Exception):
    """The booking isn't paid, or the party is already in."""


def check_in(booking, staff):
    """Let a party in at the door (4.2). The booking records who and
    when, and the audit entry's reason is the status reached, so staff
    type nothing at the door (4.9). A booking can only be checked in
    once, and only when it's paid."""
    with transaction.atomic():
        booking = Booking.objects.select_for_update().get(pk=booking.pk)
        if (booking.status != Booking.Status.PAID
                or booking.checked_in_at is not None):
            raise CheckInRefused()
        booking.checked_in_at = timezone.now()
        booking.checked_in_by = staff
        booking.save(update_fields=['checked_in_at', 'checked_in_by'])
        log_action(staff, AuditLogEntry.Action.CHECKED_IN, 'Checked in',
                   booking=booking)
    return booking


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
        max_tickets=get_settings().max_tickets_per_booking,
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
