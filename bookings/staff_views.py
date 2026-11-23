from django.contrib import messages
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from staff.models import AuditLogEntry
from staff.views import staff_permission_required
from venue.models import get_settings

from .models import Cancellation, SeatBooking
from .services import (
    CancellationNotAllowed,
    approve_cancellation,
    decline_cancellation,
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
