"""Sending the emails waiting in the outbox (architecture 4.2, 4.32)."""

import logging
from smtplib import SMTPException

from django.core.mail import EmailMultiAlternatives
from django.utils import timezone

from .models import OutboundEmail

logger = logging.getLogger(__name__)

# After this many failed tries an email is marked failed and left for
# staff on the needs-attention page (4.32).
MAX_ATTEMPTS = 5


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
