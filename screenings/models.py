from datetime import timedelta

from django.conf import settings
from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import (
    DateTimeRangeField,
    RangeBoundary,
    RangeOperators,
)
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class Film(models.Model):
    """A film or event in the local catalogue, filled from TMDb or by hand
    (architecture 4.1, 4.15)."""

    class AgeRating(models.TextChoices):
        U = 'U', 'U'
        PG = 'PG', 'PG'
        TWELVE_A = '12A', '12A'
        TWELVE = '12', '12'
        FIFTEEN = '15', '15'
        EIGHTEEN = '18', '18'

    tmdb_id = models.PositiveIntegerField(null=True, blank=True, unique=True)
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    synopsis = models.TextField(blank=True)
    poster_path = models.CharField(max_length=200, blank=True)
    trailer_key = models.CharField(max_length=50, blank=True)
    age_rating = models.CharField(
        max_length=3, choices=AgeRating.choices, blank=True
    )
    duration_minutes = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1)]
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['title']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # Set once, so the film's address doesn't change if the title does.
        if not self.slug:
            self.slug = self._unique_slug()
        super().save(*args, **kwargs)

    def _unique_slug(self):
        base = slugify(self.title) or 'film'
        slug, number = base, 2
        while Film.objects.filter(slug=slug).exists():
            slug = f'{base}-{number}'
            number += 1
        return slug


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


class TicketClass(models.Model):
    """How a whole showing is priced, such as Silver Screen. Its default
    price is a suggestion staff can change per screening (4.1, 4.18)."""

    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    default_price_pence = models.PositiveIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'ticket classes'

    def __str__(self):
        return self.name


class TicketType(models.Model):
    """Who a seated ticket is for: adult, student, OAP or child. Infants
    are a headcount on the booking, not a ticket type (4.2)."""

    name = models.CharField(max_length=30, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class TsTzRange(models.Func):
    """PostgreSQL's timestamp range, built from two datetime columns."""

    function = 'TSTZRANGE'
    output_field = DateTimeRangeField()


class Screening(models.Model):
    """A film on a screen at a time. It holds the screen from date_time to
    ends_at, and no two screenings on a screen may overlap (4.1)."""

    film = models.ForeignKey(
        Film, on_delete=models.PROTECT, related_name='screenings'
    )
    screen = models.ForeignKey(
        Screen, on_delete=models.PROTECT, related_name='screenings'
    )
    ticket_class = models.ForeignKey(
        TicketClass, on_delete=models.PROTECT, related_name='screenings'
    )
    date_time = models.DateTimeField()
    ends_at = models.DateTimeField(blank=True, editable=False)
    public_onsale_at = models.DateTimeField(null=True, blank=True)
    is_private = models.BooleanField(default=False)
    has_captions = models.BooleanField(default=False)
    has_audio_description = models.BooleanField(default=False)

    class Meta:
        ordering = ['date_time']
        constraints = [
            # Half-open ranges, so one screening may start at the moment
            # the previous one ends.
            ExclusionConstraint(
                name='no_overlapping_screenings',
                expressions=[
                    (
                        TsTzRange('date_time', 'ends_at', RangeBoundary()),
                        RangeOperators.OVERLAPS,
                    ),
                    ('screen', RangeOperators.EQUAL),
                ],
                violation_error_message=(
                    'This screening overlaps another screening on the same '
                    'screen, including trailer and turnaround time.'
                ),
            ),
        ]

    def __str__(self):
        when = timezone.localtime(self.date_time)
        return f'{self.film}, {when:%a %d %b %Y %H:%M}, {self.screen}'

    def calculate_ends_at(self):
        minutes = (
            settings.SCREENING_TRAILER_MINUTES
            + self.film.duration_minutes
            + settings.SCREENING_TURNAROUND_MINUTES
        )
        return self.date_time + timedelta(minutes=minutes)

    def clean(self):
        # Set before Django validates the constraint, so a staff form
        # gets the overlap message instead of a database error.
        if self.film_id and self.date_time:
            self.ends_at = self.calculate_ends_at()
        super().clean()

    def save(self, *args, **kwargs):
        self.ends_at = self.calculate_ends_at()
        super().save(*args, **kwargs)
