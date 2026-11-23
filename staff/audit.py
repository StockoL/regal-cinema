"""Writing the audit log (architecture 4.9)."""

from .models import AuditLogEntry


def log_action(actor, action_type, reason, booking=None, voucher=None):
    """Record who did a sensitive action and why. The reason is
    required: nobody refunds or cancels invisibly."""
    if not reason or not reason.strip():
        raise ValueError('An audit entry needs a reason.')
    return AuditLogEntry.objects.create(
        actor=actor, action_type=action_type, reason=reason.strip(),
        related_booking=booking, related_voucher=voucher,
    )
