"""Clearing the cached seat layouts when the seat plan changes (4.33)."""

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Seat, SeatingLayout
from .services import clear_layout_seats


@receiver([post_save, post_delete], sender=Seat)
@receiver([post_save, post_delete], sender=SeatingLayout)
def seat_plan_changed(sender, instance, **kwargs):
    clear_layout_seats(instance.screen_id)
