import csv
from datetime import date, timedelta

from django.contrib import messages
from django.db.models import Count, Prefetch, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from payments.base import PaymentUnavailable
from screenings.models import Screening
from staff.models import AuditLogEntry
from staff.views import staff_permission_required
from venue.models import get_settings

from .attention import stuck_payments
from .models import Booking, Cancellation, SeatBooking
from .services import (
    CancellationNotAllowed,
    CheckInRefused,
    approve_cancellation,
    check_in,
    decline_cancellation,
    find_bookings,
    impossible_reference,
    recheck_payment,
    recheck_too_soon,
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


@staff_permission_required('bookings.view_attention')
def attention(request):
    """What needs a person, each with its action beside it (4.32)."""
    return render(request, 'bookings/staff/attention.html', {
        'stuck_payments': list(stuck_payments()),
    })


@require_POST
@staff_permission_required('bookings.view_attention')
def check_with_stripe(request, reference):
    """Ask Stripe about a payment whose webhook never came (4.32). The
    check-in search leaves pending bookings out, so this goes back to
    the staff home until the needs-attention page lists them."""
    booking = get_object_or_404(Booking, reference=reference)
    if booking.status != Booking.Status.PENDING:
        messages.error(request, f'{reference} is not waiting for payment.')
    elif recheck_too_soon(booking):
        messages.error(request, f'{reference} started paying less than five '
                                f'minutes ago. Give Stripe a little longer.')
    else:
        recheck_message(request, booking)
    return redirect('staff:home')


def recheck_message(request, booking):
    """Ask Stripe, and tell staff what it said."""
    reference = booking.reference
    try:
        paid = recheck_payment(
            booking, request.user,
            'Paid on Stripe with no webhook. Found by Check with Stripe.',
        )
    except PaymentUnavailable:
        messages.error(request, 'The site could not reach Stripe. Try '
                                'again in a minute.')
        return
    if not paid:
        messages.info(request, f'Stripe says {reference} has not been paid.')
        return
    booking.refresh_from_db()
    if booking.status == Booking.Status.REFUNDED:
        messages.error(request, f'{reference} was paid after its seats '
                                f'had gone, so the payment is being '
                                f'refunded.')
    else:
        messages.success(request, f'Stripe says {reference} was paid, '
                                  f'so it is now confirmed.')


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


@staff_permission_required('bookings.view_bookings')
def guest_list_download(request, pk):
    """The guest list as a CSV file, to keep or print if the site goes
    down before the door opens (4.32)."""
    screening = get_object_or_404(Screening.objects.select_related('film'),
                                  pk=pk)
    name = (f'guest-list-{screening.film.slug}-'
            f'{timezone.localdate(screening.date_time).isoformat()}.csv')
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{name}"'
    writer = csv.writer(response)
    writer.writerow(['Reference', 'Customer', 'Seats', 'Under 2s', 'Status',
                     'Checked in'])
    for booking in guests(screening):
        seats = '; '.join(
            f'{sold.seat.label}, {sold.ticket_type.name}'
            + (f'. {sold.ticket_type.proof_reminder}'
               if sold.ticket_type.proof_reminder else '')
            for sold in booking.seats.all()
        )
        checked_in = (
            timezone.localtime(booking.checked_in_at).strftime('%H:%M')
            if booking.checked_in_at else ''
        )
        writer.writerow([
            booking.reference,
            booking.user.email if booking.user else 'At the venue',
            seats, booking.infant_count, booking.get_status_display(),
            checked_in,
        ])
    return response


@staff_permission_required('bookings.view_bookings')
def screening_list(request):
    """One day's screenings, today by default, each with its bookings
    and a link to its guest list (4.32). Staff see private and
    cancelled screenings too, labelled."""
    try:
        day = date.fromisoformat(request.GET.get('date', ''))
    except ValueError:
        day = timezone.localdate()
    screenings = (
        Screening.objects.filter(date_time__date=day)
        .select_related('film', 'screen')
        .annotate(booking_count=Count(
            'bookings', filter=Q(bookings__status__in=AT_THE_DOOR),
        ))
        .order_by('date_time')
    )
    return render(request, 'bookings/staff/screening_list.html', {
        'day': day,
        'previous_day': day - timedelta(days=1),
        'next_day': day + timedelta(days=1),
        'screenings': screenings,
    })
