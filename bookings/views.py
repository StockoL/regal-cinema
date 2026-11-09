from django.shortcuts import get_object_or_404, redirect, render

from screenings.models import Screening

from .services import seat_plan


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
    return render(request, 'bookings/screening_seats.html', {
        'screening': screening,
        'seat_groups': seat_plan(screening),
        'ticked': {seat.pk for seat in chosen_seats(request, screening)},
        'error': error,
    })


def screening_tickets(request, pk):
    """A ticket type for each chosen seat (journey 2, "Ticket types")."""
    screening = public_screening(pk)
    seats = chosen_seats(request, screening)
    if not seats:
        return redirect('bookings:screening_seats', pk=screening.pk)
    return render(request, 'bookings/screening_tickets.html', {
        'screening': screening,
        'seats': [(seat, seat.label) for seat in seats],
    })
