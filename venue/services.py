from django.db import transaction

from staff.audit import log_action
from staff.models import AuditLogEntry

from .models import VenueSettings, get_settings


def set_online_sales_paused(paused, actor, reason):
    """Pause or resume online sales, logged with who and why (4.23).
    The row is locked, so a double click or two people at once change
    it once. Returns whether anything changed."""
    get_settings()
    with transaction.atomic():
        venue = VenueSettings.objects.select_for_update().get(pk=1)
        if venue.online_sales_paused == paused:
            return False
        venue.online_sales_paused = paused
        venue.save(update_fields=['online_sales_paused'])
        done = 'Paused' if paused else 'Resumed'
        log_action(actor, AuditLogEntry.Action.SETTING_CHANGED,
                   f'{done} online sales: {reason.strip()}')
    return True
