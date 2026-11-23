from django.contrib import messages
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from screenings.models import Screening
from staff.models import AuditLogEntry
from staff.views import staff_permission_required
from venue.models import get_settings

from .models import Booking, Cancellation, SeatBooking
from .services import (
    CancellationNotAllowed,
    CheckInRefused,
    approve_cancellation,
    check_in,
    decline_cancellation,
    find_bookings,
    impossible_reference,
)

DECISIONS = [
    AuditLogEntry.Action.CANCELLATION_DECLINED,
    AuditLogEntry.Action.BOOKING_CANCELLED,
    AuditLogEntry.Action.VOUCHER_ISSUED,
    AuditLogEntry.Action.REFUND,
]


@staff_permission_required('bookings.cancel_booking')
def cancellation_list(request):
    """Customers' requests waiting for a decision, oldest first, with
    the recent decisions from the audit log (4.22; wireframe 21)."""
    waiting = (
        Cancellation.objects.filter(status=Cancellation.Status.REQUESTED)
        .select_related('booking__screening__film', 'booking__user')
        .prefetch_related(Prefetch(
            'booking__seats',
            queryset=SeatBooking.objects.select_related('seat',
                                                        'ticket_type'),
        ))
        .order_by('requested_at')
    )
    fee = get_settings().cancellation_fee_pence
    for cancellation in waiting:
        charged = cancellation.booking.amount_charged_pence
        cancellation.voucher_pence = (
            None if charged is None else max(charged - fee, 0)
        )
    recent = (
        AuditLogEntry.objects.filter(action_type__in=DECISIONS)
        .select_related('actor', 'related_booking')[:10]
    )
    return render(request, 'bookings/staff/cancellation_list.html', {
        'waiting': waiting,
        'fee_pence': fee,
        'recent': recent,
    })


@require_POST
@staff_permission_required('bookings.cancel_booking')
def cancellation_approve(request, pk):
    """Approve one request: the customer gets a voucher and the seats go
    back on sale (4.22). Approving issues the voucher, so this needs
    cancel_booking, not issue_voucher."""
    cancellation = get_object_or_404(Cancellation, pk=pk)
    reference = cancellation.booking.reference
    try:
        cancellation = approve_cancellation(cancellation, request.user,
                                            request.POST.get('note', ''))
    except ValueError:
        messages.error(request, f'Write a note to the customer to approve '
                                f'{reference}.')
    except CancellationNotAllowed:
        messages.error(request, f'The request for {reference} has already '
                                f'been decided.')
    else:
        voucher = cancellation.booking.vouchers_issued.get()
        messages.success(request, f'Approved {reference}. Voucher '
                                  f'{voucher.code} has been emailed to the '
                                  f'customer.')
    return redirect('bookings_staff:cancellation_list')


@require_POST
@staff_permission_required('bookings.cancel_booking')
def cancellation_decline(request, pk):
    """Decline one request, with the note the customer will see."""
    cancellation = get_object_or_404(Cancellation, pk=pk)
    reference = cancellation.booking.reference
    try:
        decline_cancellation(cancellation, request.user,
                             request.POST.get('note', ''))
    except ValueError:
        messages.error(request, f'Write a note to the customer to decline '
                                f'{reference}.')
    except CancellationNotAllowed:
        messages.error(request, f'The request for {reference} has already '
                                f'been decided.')
    else:
        messages.success(request, f'Declined the request for {reference}. '
                                  f'The customer has been told.')
    return redirect('bookings_staff:cancellation_list')


@staff_permission_required('bookings.view_bookings')
def check_in_search(request):
    """The door: find a booking by reference or email and let the party
    in (journey 14; 4.32; wireframe 22)."""
    query = request.GET.get('q', '').strip()
    found = []
    if query:
        found = find_bookings(query).prefetch_related(Prefetch(
            'seats', queryset=SeatBooking.objects.live()
            .select_related('seat', 'ticket_type')
            .order_by('-seat__area', 'seat__row_index', 'seat__column_index'),
        ))
    return render(request, 'bookings/staff/check_in.html', {
        'query': query,
        'found': found,
        'can_check_in': request.user.has_perm('bookings.check_in_booking'),
        'impossible_reference': impossible_reference(query),
    })


@require_POST
@staff_permission_required('bookings.check_in_booking')
def check_in_booking(request, reference):
    """Check one party in, then come back to the same search."""
    booking = get_object_or_404(Booking, reference=reference)
    try:
        check_in(booking, request.user)
    except CheckInRefused:
        if booking.checked_in_at:
            messages.error(request, f'{reference} is already checked in.')
        else:
            messages.error(request, f"{reference} isn't paid, so it can't "
                                    f'be checked in.')
    else:
        messages.success(request, f'Checked in {reference}.')
    return redirect(f"{reverse('bookings_staff:check_in')}?q={reference}")


# The bookings that will be at the door: a request still waiting stands
# until staff decide (4.22).
AT_THE_DOOR = [Booking.Status.PAID, Booking.Status.CANCELLATION_REQUESTED]


def guests(screening):
    """A screening's bookings for the door, with their seats."""
    return list(
        screening.bookings.filter(status__in=AT_THE_DOOR)
        .select_related('user', 'checked_in_by')
        .prefetch_related(Prefetch(
            'seats', queryset=SeatBooking.objects.live()
            .select_related('seat', 'ticket_type')
            .order_by('-seat__area', 'seat__row_index', 'seat__column_index'),
        ))
        .order_by('reference')
    )


@staff_permission_required('bookings.view_bookings')
def guest_list(request, pk):
    """Everyone expected at one screening, to print or take to the door
    if the site is down (journey 14; 4.32)."""
    screening = get_object_or_404(
        Screening.objects.select_related('film', 'screen'), pk=pk
    )
    bookings = guests(screening)
    return render(request, 'bookings/staff/guest_list.html', {
        'screening': screening,
        'bookings': bookings,
        'seat_count': sum(len(b.seats.all()) for b in bookings),
        'checked_in_count': sum(1 for b in bookings if b.checked_in_at),
    })
