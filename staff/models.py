from django.conf import settings
from django.db import models


class AuditLogEntry(models.Model):
    """Who did something sensitive, what, and why. Written by the same
    action that does it, through staff.audit.log_action, so it can't be
    skipped (architecture 4.9)."""

    class Action(models.TextChoices):
        REFUND = 'refund', 'Refund'
        SCREENING_CANCELLED = 'screening_cancelled', 'Screening cancelled'
        BOOKING_CANCELLED = 'booking_cancelled', 'Booking cancelled'
        VOUCHER_ISSUED = 'voucher_issued', 'Voucher issued'
        CANCELLATION_DECLINED = (
            'cancellation_declined', 'Cancellation declined'
        )
        VOUCHER_DEACTIVATED = 'voucher_deactivated', 'Voucher deactivated'
        SETTING_CHANGED = 'setting_changed', 'Setting changed'
        ORDER_STATUS_CHANGED = (
            'order_status_changed', 'Order status changed'
        )
        CHECKED_IN = 'checked_in', 'Checked in'
        DISPUTE_OPENED = 'dispute_opened', 'Dispute opened'
        DISPUTE_CLOSED = 'dispute_closed', 'Dispute closed'
        PAYMENT_CONFIRMED = 'payment_confirmed', 'Payment confirmed'

    # Staff accounts are deactivated, never deleted, so the log always
    # names a real person, or the system user (4.21).
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='audit_entries',
    )
    action_type = models.CharField(max_length=25, choices=Action.choices)
    related_booking = models.ForeignKey(
        'bookings.Booking', on_delete=models.PROTECT,
        related_name='audit_entries', null=True, blank=True,
    )
    related_voucher = models.ForeignKey(
        'membership.Voucher', on_delete=models.PROTECT,
        related_name='audit_entries', null=True, blank=True,
    )
    reason = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'audit log entries'
        permissions = [
            ('view_sales_dashboard', 'Can see the reports'),
        ]

    def __str__(self):
        return f'{self.get_action_type_display()} by {self.actor}'
