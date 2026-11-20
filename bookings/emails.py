"""Writing emails to the outbox and sending them (architecture 4.2, 4.32)."""

import logging
from smtplib import SMTPException

from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone

from .models import OutboundEmail

logger = logging.getLogger(__name__)

# After this many failed tries an email is marked failed and left for
# staff on the needs-attention page (4.32).
MAX_ATTEMPTS = 5


def queue_email(kind, recipient, template, context, booking=None):
    """Write an email to the outbox and send it once the transaction it
    belongs to has committed (4.2). Its subject, plain text and HTML
    come from templates/emails/, the plain text first."""
    email = OutboundEmail.objects.create(
        kind=kind, booking=booking, recipient=recipient,
        subject=render_to_string(f'emails/{template}_subject.txt',
                                 context).strip(),
        text_body=render_to_string(f'emails/{template}.txt', context),
        html_body=render_to_string(f'emails/{template}.html', context),
    )
    transaction.on_commit(lambda: send_outbound_email(email.pk))
    return email


def queue_booking_confirmation(booking):
    """The confirmation, for a booking with an account behind it. A
    walk-up sale at the venue needs none (4.14)."""
    if booking.user is None:
        return None
    seats = booking.seats.live().select_related('seat', 'ticket_type')
    return queue_email(
        OutboundEmail.Kind.CONFIRMATION, booking.user.email,
        'booking_confirmation', {
            'booking': booking,
            'seats': seats.order_by('-seat__area', 'seat__row_index',
                                    'seat__column_index'),
        },
        booking=booking,
    )


def send_outbound_email(email_pk):
    """Send one queued email and record what happened. A failure is
    counted and kept, never raised, so it can't undo the change the
    email reports. An email already sent or given up on is left alone."""
    email = OutboundEmail.objects.get(pk=email_pk)
    if email.status != OutboundEmail.Status.QUEUED:
        return
    message = EmailMultiAlternatives(
        email.subject, email.text_body, None, [email.recipient],
    )
    if email.html_body:
        message.attach_alternative(email.html_body, 'text/html')
    email.attempts += 1
    try:
        message.send()
    except (SMTPException, OSError) as error:
        logger.warning('Email %s could not be sent: %s', email.pk, error)
        email.last_error = str(error)
        if email.attempts >= MAX_ATTEMPTS:
            email.status = OutboundEmail.Status.FAILED
    else:
        email.status = OutboundEmail.Status.SENT
        email.sent_at = timezone.now()
    email.save(update_fields=['attempts', 'last_error', 'status',
                              'sent_at'])
