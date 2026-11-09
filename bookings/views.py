from django.contrib import messages
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from screenings.models import Screening

from .basket import BasketError
from .models import Booking
from .services import (
    HoldTimeUsedUp,
    SeatsUnavailable,
    amend_booking,
    cancel_pending_booking,
    seat_plan,
    start_booking,
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
