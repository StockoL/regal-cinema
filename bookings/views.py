from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.db.models import Prefetch, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from payments.base import PaymentUnavailable
from regal.ratelimit import rate_limit
from screenings.models import Screening
from venue.models import get_settings

from .basket import BasketError
from .forms import CancellationRequestForm
from .handover import remember_booking
from .models import Booking, SeatBooking
from .services import (
    CancellationNotAllowed,
    HoldTimeUsedUp,
    HoldsExpired,
    SeatsUnavailable,
    amend_booking,
    basket_total,
    cancel_pending_booking,
    cancellation_state,
    request_cancellation,
    seat_plan,
    start_booking,
    start_payment,
)


def public_screening(pk):
    """A screening the public can book. Private ones aren't found."""
    return get_object_or_404(
        Screening.objects.select_related('film', 'screen'),
        pk=pk, is_private=False, film__is_active=True,
    )


def session_key_for(screening):
    return f'seats:{screening.pk}'


def chosen_seats(request, screening):
    """The seats this visitor ticked for this screening, kept in the
    session between steps. Only seats the screening actually uses."""
    ids = request.session.get(session_key_for(screening), [])
    return list(screening.seats().filter(pk__in=ids).order_by(
        '-area', 'row_index', 'column_index'
    ))


def owner_filter(request):
    """Matches bookings this browser or account made."""
    owner = Q(holds__session_key=request.session.session_key or '-')
    if request.user.is_authenticated:
        owner |= Q(user=request.user)
    return owner


def own_pending_booking(request, screening):
    """This customer's pending booking for the screening, if they've
    already held seats and come back to change them (4.8 step 11)."""
    return (
        Booking.objects.filter(owner_filter(request), screening=screening,
                               status=Booking.Status.PENDING)
        .distinct().order_by('-created_at').first()
    )


def screening_seats(request, pk):
    """Choosing seats for one screening (journey 2). A cancelled
    screening says so plainly (4.11)."""
    screening = public_screening(pk)
    if screening.is_cancelled:
        return render(request, 'bookings/screening_cancelled.html',
                      {'screening': screening}, status=410)
    error = None
    if request.method == 'POST' and not screening.online_sales_closed:
        ids = [int(i) for i in request.POST.getlist('seats') if i.isdigit()]
        if ids:
            request.session[session_key_for(screening)] = ids
            return redirect('bookings:screening_tickets', pk=screening.pk)
        error = 'Choose at least one seat.'
    booking = own_pending_booking(request, screening)
    ticked = {seat.pk for seat in chosen_seats(request, screening)}
    if not ticked and booking:
        ticked = set(booking.holds.values_list('seat', flat=True))
    return render(request, 'bookings/screening_seats.html', {
        'screening': screening,
        'seat_areas': seat_plan(screening, own_booking=booking),
        'ticked': ticked,
        'error': error,
    })


def offered_ticket_types(screening):
    """The ticket types the film's rating allows that have a price at
    this screening, each with its price in pence."""
    allowed = set(screening.film.ticket_types())
    return [
        (price.ticket_type, price.price_pence)
        for price in screening.prices.select_related('ticket_type')
        .order_by('ticket_type__name')
        if price.ticket_type in allowed
    ]


@rate_limit('hold-seats', limit=20, window=10 * 60)
def screening_tickets(request, pk):
    """A ticket type for each chosen seat and any infants, then the
    seats are held in a pending booking (journey 2; 4.8 step 3)."""
    screening = public_screening(pk)
    seats = chosen_seats(request, screening)
    if not seats or screening.is_cancelled:
        return redirect('bookings:screening_seats', pk=screening.pk)
    offered = offered_ticket_types(screening)
    types_by_id = {str(ticket_type.pk): ticket_type
                   for ticket_type, _ in offered}
    booking = own_pending_booking(request, screening)
    held_types = {}
    if booking:
        held_types = {hold.seat_id: str(hold.ticket_type_id)
                      for hold in booking.holds.all()}
    if request.method == 'POST':
        picked = {seat.pk: request.POST.get(f'type_{seat.pk}', '')
                  for seat in seats}
        infants = request.POST.get('infants', '0')
        infants = int(infants) if infants.isdigit() else 0
    else:
        picked = {seat.pk: held_types.get(seat.pk, '') for seat in seats}
        infants = booking.infant_count if booking else 0
    error = None

    if request.method == 'POST' and screening.online_sales_closed:
        return redirect('bookings:screening_seats', pk=screening.pk)
    if request.method == 'POST':
        choices = [(seat, types_by_id.get(picked[seat.pk]))
                   for seat in seats]
        if any(ticket_type is None for _, ticket_type in choices):
            error = 'Choose a ticket type for each seat.'
        else:
            if not request.session.session_key:
                request.session.save()
            user = request.user if request.user.is_authenticated else None
            try:
                if booking:
                    booking = amend_booking(
                        booking, choices, infants,
                        request.session.session_key, user=user,
                    )
                else:
                    booking = start_booking(
                        screening, choices, infants,
                        request.session.session_key, user=user,
                    )
            except HoldTimeUsedUp:
                return hold_time_used_up(request, screening, booking)
            except BasketError as rule:
                error = str(rule)
            except SeatsUnavailable as taken:
                return seats_taken(request, screening, seats, taken.seats)
            else:
                del request.session[session_key_for(screening)]
                remember_booking(request, booking)
                return redirect('bookings:booking_checkout',
                                reference=booking.reference)

    return render(request, 'bookings/screening_tickets.html', {
        'screening': screening,
        'seats': [(seat, seat.label) for seat in seats],
        'picked': picked,
        'ticket_types': offered,
        'infants': infants,
        'error': error,
    })


def hold_time_used_up(request, screening, booking):
    """The booking has had its 30 minutes: let the seats go and start
    again from the seats, which stay ticked if they're still free."""
    cancel_pending_booking(booking)
    messages.info(
        request,
        "You've had these seats for 30 minutes, the longest we can keep "
        'them. Please choose them again.',
    )
    return redirect('bookings:screening_seats', pk=screening.pk)


def seats_taken(request, screening, seats, taken):
    """Back to the seats with the taken ones named and unticked, and the
    customer's other choices kept (4.8 step 4)."""
    request.session[session_key_for(screening)] = [
        seat.pk for seat in seats if seat not in taken
    ]
    names = ', '.join(seat.label for seat in taken)
    messages.error(
        request,
        f'{names} was taken while you were choosing. Your other seats '
        'are still ticked.',
    )
    return redirect('bookings:screening_seats', pk=screening.pk)


def owned_pending_booking(request, reference):
    """The pending booking with this reference, if this browser or
    account made it. Anyone else gets a 404, so a guessed reference
    shows nothing."""
    booking = (
        Booking.objects.filter(owner_filter(request), reference=reference,
                               status=Booking.Status.PENDING)
        .select_related('screening__film').distinct().first()
    )
    if booking is None:
        raise Http404('No such booking.')
    return booking


def booking_checkout(request, reference):
    """Where a pending booking goes next. Payment comes with Stripe
    (4.13)."""
    booking = owned_pending_booking(request, reference)
    holds = booking.holds.select_related('seat', 'ticket_type').order_by(
        '-seat__area', 'seat__row_index', 'seat__column_index'
    )
    expiries = [hold.expires_at for hold in holds]
    return render(request, 'bookings/booking_checkout.html', {
        'booking': booking,
        'holds': holds,
        'held_until': min(expiries) if expiries else None,
        'total_pence': basket_total(booking, holds),
        # Stripe's cancel link brings the customer back here (4.13 step 6).
        'not_completed': request.GET.get('payment') == 'not-completed',
    })


@require_POST
def booking_pay(request, reference):
    """The customer chose Pay (4.13 step 3). Paying needs an account
    (4.16), so a visitor logs in first and comes back to the checkout
    page with their seats. Then they're sent to Stripe's page."""
    checkout = reverse('bookings:booking_checkout', args=[reference])
    if not request.user.is_authenticated:
        return redirect_to_login(checkout)
    booking = owned_pending_booking(request, reference)
    confirming = reverse('bookings:booking_confirming', args=[reference])
    try:
        session = start_payment(
            booking,
            success_url=request.build_absolute_uri(confirming),
            cancel_url=request.build_absolute_uri(
                f'{checkout}?payment=not-completed'
            ),
        )
    except HoldsExpired:
        messages.error(request, 'Your hold on these seats ran out. '
                                'Please choose your seats again.')
        return redirect('bookings:screening_seats', pk=booking.screening.pk)
    except PaymentUnavailable:
        # Nothing was saved, so the seats are held as they were (4.32).
        messages.error(request, "We couldn't reach the payment provider. "
                                'Your seats are still held, so please try '
                                'again.')
        return redirect(checkout)
    # 303, so the browser fetches Stripe's page rather than posting again.
    response = redirect(session.url)
    response.status_code = 303
    return response


def booking_confirming(request, reference):
    """Where Stripe sends the customer back to. Coming back confirms
    nothing: the booking is paid only once the webhook says so (4.13
    step 4). Until then the page says it's still being confirmed."""
    booking = (
        Booking.objects.filter(owner_filter(request), reference=reference)
        .exclude(status=Booking.Status.CANCELLED)
        .select_related('screening__film').distinct().first()
    )
    if booking is None:
        raise Http404('No such booking.')
    seats = booking.seats.live().select_related('seat', 'ticket_type')
    return render(request, 'bookings/booking_confirming.html', {
        'booking': booking,
        'paid': booking.status == Booking.Status.PAID,
        # Paid after the seats had gone, and refunded (4.13).
        'refunded': booking.status == Booking.Status.REFUNDED,
        'seats': seats.order_by('-seat__area', 'seat__row_index',
                                'seat__column_index'),
    })


@login_required
def booking_list(request):
    """My bookings: everything the customer has paid for, upcoming first
    and then past, each with its status. A cancelled booking stays with
    its status rather than disappearing (journey 7; brief decision 6).
    Unpaid bookings are left out: they're still at checkout."""
    bookings = (
        request.user.bookings.exclude(status=Booking.Status.PENDING)
        .select_related('screening__film', 'screening__screen')
        .prefetch_related(Prefetch(
            'seats',
            queryset=SeatBooking.objects.select_related('seat',
                                                        'ticket_type')
            .order_by('-seat__area', 'seat__row_index', 'seat__column_index'),
        ), 'vouchers_issued')
        .order_by('screening__date_time')
    )
    now = timezone.now()
    venue = get_settings()
    for booking in bookings:
        booking.cancel_state = cancellation_state(booking, venue)
    return render(request, 'bookings/booking_list.html', {
        'upcoming': [b for b in bookings if b.screening.date_time >= now],
        'past': [b for b in reversed(bookings)
                 if b.screening.date_time < now],
    })


@login_required
def cancellation_request(request, reference):
    """Asking to cancel a booking from My bookings (journey 7, 4.22).
    Outside the cutoff the customer sends a request for staff to decide;
    inside it, the page gives the box office instead. A booking that
    can't be cancelled online has no page."""
    booking = get_object_or_404(
        request.user.bookings.select_related('screening__film',
                                             'screening__screen'),
        reference=reference,
    )
    state = cancellation_state(booking)
    if state is None:
        raise Http404("This booking can't be cancelled online.")
    venue = get_settings()
    form = CancellationRequestForm(request.POST or None)
    if state == 'open' and request.method == 'POST' and form.is_valid():
        try:
            request_cancellation(booking, form.cleaned_data['reason'])
        except CancellationNotAllowed:
            raise Http404("This booking can't be cancelled online.")
        messages.success(request, 'Your request has been sent. Staff will '
                                  'confirm it, and your booking stands '
                                  'until they do.')
        return redirect('bookings:booking_list')
    charged = booking.amount_charged_pence
    return render(request, 'bookings/cancellation_request.html', {
        'booking': booking,
        'state': state,
        'form': form,
        'venue': venue,
        'voucher_pence': (None if charged is None
                          else max(charged - venue.cancellation_fee_pence,
                                   0)),
    })


@require_POST
def booking_cancel(request, reference):
    """Let the held seats go now (journey 2, "Cancel")."""
    booking = owned_pending_booking(request, reference)
    screening = booking.screening
    cancel_pending_booking(booking)
    request.session.pop(session_key_for(screening), None)
    messages.success(request, 'Your seats have been released.')
    return redirect('bookings:screening_seats', pk=screening.pk)
