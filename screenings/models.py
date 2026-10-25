from django.db import models


class Screen(models.Model):
    """An auditorium. Retired by marking inactive, never deleted once it
    has history (architecture 4.21)."""

    name = models.CharField(max_length=50, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def capacity(self):
        """Counted from the seat plan, so it can't drift from it."""
        return self.seats.count()


class Seat(models.Model):
    """One seat in a screen's fixed plan. Area describes where it is; it
    doesn't change the price (architecture 4.1)."""

    class Area(models.TextChoices):
        STALLS = 'stalls', 'Stalls'
        CIRCLE = 'circle', 'Circle'

    screen = models.ForeignKey(
        Screen, on_delete=models.CASCADE, related_name='seats'
    )
    row_label = models.CharField(max_length=3)
    seat_number = models.PositiveSmallIntegerField()
    area = models.CharField(max_length=10, choices=Area.choices)

    class Meta:
        ordering = ['screen', 'row_label', 'seat_number']
        constraints = [
            models.UniqueConstraint(
                fields=['screen', 'row_label', 'seat_number'],
                name='unique_seat_per_screen',
            ),
        ]

    def __str__(self):
        return (
            f'Row {self.row_label}, seat {self.seat_number}, '
            f'{self.get_area_display().lower()}'
        )
