from django.db import transaction

from staff.audit import log_action
from staff.models import AuditLogEntry

from .models import SYSTEM_USER_EMAIL, User


class NotACustomerAccount(Exception):
    """Staff accounts and the system user are managed in the admin, not
    from the customer accounts page (4.32)."""


def deactivate_account(account, staff, reason):
    """Stop a customer account logging in, and sign it out wherever it
    is, since Django drops an inactive user's session. Its bookings
    stay. Logged with the reason. Returns whether anything changed."""
    return set_active(account, staff, reason, active=False)


def reactivate_account(account, staff, reason):
    """Undo a deactivation, logged the same way."""
    return set_active(account, staff, reason, active=True)


def set_active(account, staff, reason, active):
    if account.is_staff or account.email == SYSTEM_USER_EMAIL:
        raise NotACustomerAccount()
    if not reason.strip():
        raise ValueError('Deactivating or reactivating needs a reason.')
    with transaction.atomic():
        account = User.objects.select_for_update().get(pk=account.pk)
        if account.is_active == active:
            return False
        account.is_active = active
        account.save(update_fields=['is_active'])
        log_action(staff,
                   AuditLogEntry.Action.ACCOUNT_REACTIVATED if active
                   else AuditLogEntry.Action.ACCOUNT_DEACTIVATED,
                   reason, user=account)
    return True
