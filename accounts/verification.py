"""The verification email: a signed, time-limited link, so nothing new
is stored until the customer follows it (architecture 4.16)."""

import logging
from smtplib import SMTPException

from django.core import signing
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from .models import User

logger = logging.getLogger(__name__)

SALT = 'accounts.verify-email'
# Three days, the same as a password reset link.
LINK_MAX_AGE = 60 * 60 * 24 * 3


def make_token(user):
    # The address is signed too, so a link sent to an old address
    # can't verify a new one.
    return signing.dumps({'user': user.pk, 'email': user.email}, salt=SALT)


def send_verification_email(request, user):
    """Send the link. A failure is logged, never shown: verification is
    a reminder, so it mustn't stop anyone registering."""
    link = request.build_absolute_uri(
        reverse('accounts:verify_email', args=[make_token(user)])
    )
    context = {'email': user.email, 'link': link}
    try:
        send_mail(
            render_to_string('accounts/verify_email_subject.txt').strip(),
            render_to_string('accounts/verify_email.txt', context),
            None, [user.email],
        )
    except (SMTPException, OSError):
        logger.exception('Could not send the verification email.')


def verify(token):
    """Mark the address verified if the link is good. Returns the user,
    or None for a link that's broken, too old or for another address."""
    try:
        data = signing.loads(token, salt=SALT, max_age=LINK_MAX_AGE)
    except signing.BadSignature:
        return None
    user = User.objects.filter(pk=data['user'], email=data['email']).first()
    if user and user.email_verified_at is None:
        user.email_verified_at = timezone.now()
        user.save(update_fields=['email_verified_at'])
    return user
