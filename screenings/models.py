from datetime import timedelta

from django.conf import settings
from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import (
    DateTimeRangeField,
    RangeBoundary,
    RangeOperators,
)
from django.core.exceptions import ValidationError
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


class SeatingLayout(models.Model):
    """One arrangement of a screen's stalls, such as standard rows or
    tables. The circle is fixed and appears in every layout (4.1)."""

    screen = models.ForeignKey(
        Screen, on_delete=models.CASCADE, related_name='layouts'
    )
    name = models.CharField(max_length=50)
    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ['screen', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=['screen', 'name'],
                name='unique_layout_name_per_screen',
            ),
            models.UniqueConstraint(
                fields=['screen'],
                condition=models.Q(is_default=True),
                name='one_default_layout_per_screen',
            ),
        ]

    def __str__(self):
        return f'{self.screen}: {self.name}'


class Seat(models.Model):
    """One seat in a screen. With no layout it's fixed and appears in
    every layout, which is how the circle works. With a layout it belongs
    to that stalls arrangement only. Area describes where it is; it
    doesn't change the price (architecture 4.1)."""

    class Area(models.TextChoices):
        STALLS = 'stalls', 'Stalls'
        CIRCLE = 'circle', 'Circle'

    screen = models.ForeignKey(
        Screen, on_delete=models.CASCADE, related_name='seats'
    )
    layout = models.ForeignKey(
        SeatingLayout, on_delete=models.CASCADE, related_name='seats',
        null=True, blank=True,
    )
    row_label = models.CharField(max_length=3, blank=True)
    number = models.PositiveSmallIntegerField()
    table_number = models.PositiveSmallIntegerField(null=True, blank=True)
    area = models.CharField(max_length=10, choices=Area.choices)
    # Where the seat sits on the map. Empty columns are aisles and gaps.
    row_index = models.PositiveSmallIntegerField()
    column_index = models.PositiveSmallIntegerField()
    is_wheelchair_space = models.BooleanField(default=False)
    # Beside a wheelchair space, offered first to a companion (4.17).
    is_companion_seat = models.BooleanField(default=False)
    # False for a seat out of use. It stays in the plan but can't be sold.
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['screen', 'row_label', 'number']
        constraints = [
            models.UniqueConstraint(
                fields=['screen', 'layout', 'area', 'row_label', 'number'],
                name='unique_seat_per_layout',
            ),
            # PostgreSQL treats empty layouts as different from each
            # other, so fixed seats need their own rule.
            models.UniqueConstraint(
                fields=['screen', 'area', 'row_label', 'number'],
                condition=models.Q(layout__isnull=True),
                name='unique_fixed_seat_per_screen',
            ),
        ]

    def __str__(self):
        return self.label

    @property
    def label(self):
        """Built from the fields, not stored, so it can't disagree with
        them: "Stalls, seat 20" or "Circle, row B, seat 14"."""
        parts = [self.get_area_display()]
        if self.row_label:
            parts.append(f'row {self.row_label}')
        parts.append(f'seat {self.number}')
        return ', '.join(parts)

    def clean(self):
        super().clean()
        # The circle is reached by stairs only (4.1, 4.17).
        if self.is_wheelchair_space and self.area == self.Area.CIRCLE:
            raise ValidationError({
                'is_wheelchair_space': (
                    'A wheelchair space can only be in the stalls. The '
                    'circle is reached by stairs only.'
                ),
            })


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
    layout = models.ForeignKey(
        SeatingLayout, on_delete=models.PROTECT, related_name='screenings'
    )
    ticket_class = models.ForeignKey(
        TicketClass, on_delete=models.PROTECT, related_name='screenings'
    )
    date_time = models.DateTimeField()
    ends_at = models.DateTimeField(blank=True, editable=False)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    public_onsale_at = models.DateTimeField(null=True, blank=True)
    is_private = models.BooleanField(default=False)
    has_captions = models.BooleanField(default=False)
    has_audio_description = models.BooleanField(default=False)

    class Meta:
        ordering = ['date_time']
        constraints = [
            # Half-open ranges, so one screening may start at the moment
            # the previous one ends. Cancelled screenings are kept, hidden
            # from public listings, and no longer hold the screen (4.11).
            ExclusionConstraint(
                name='no_overlapping_screenings',
                expressions=[
                    (
                        TsTzRange('date_time', 'ends_at', RangeBoundary()),
                        RangeOperators.OVERLAPS,
                    ),
                    ('screen', RangeOperators.EQUAL),
                ],
                condition=models.Q(cancelled_at__isnull=True),
                violation_error_message=(
                    'This screening overlaps another screening on the same '
                    'screen, including trailer and turnaround time.'
                ),
            ),
        ]

    def __str__(self):
        when = timezone.localtime(self.date_time)
        return f'{self.film}, {when:%a %d %b %Y %H:%M}, {self.screen}'

    @property
    def is_cancelled(self):
        return self.cancelled_at is not None

    def seats(self):
        """The screen's fixed seats plus this screening's layout, leaving
        out seats out of use. Capacity comes from this set, worked out
        when needed, so it can't disagree with the seat plan (4.1)."""
        return self.screen.seats.filter(
            models.Q(layout__isnull=True) | models.Q(layout=self.layout_id),
            is_active=True,
        )

    @property
    def capacity(self):
        return self.seats().count()

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
        if (self.layout_id and self.screen_id
                and self.layout.screen_id != self.screen_id):
            raise ValidationError({
                'layout': 'Choose a layout that belongs to this screen.',
            })
        super().clean()

    def validate_constraints(self, exclude=None):
        # Forms leave out fields they don't show, and Django skips any
        # constraint that uses a left-out field. The overlap check uses
        # ends_at, which clean() has just set, and cancelled_at, which
        # holds its saved value, so both are safe to keep in.
        if exclude:
            exclude = set(exclude) - {'ends_at', 'cancelled_at'}
        super().validate_constraints(exclude=exclude)

    def save(self, *args, **kwargs):
        self.ends_at = self.calculate_ends_at()
        super().save(*args, **kwargs)


class ScreeningPrice(models.Model):
    """What one ticket type costs at one screening. Staff start from the
    ticket class's default and can change any line (4.1)."""

    screening = models.ForeignKey(
        Screening, on_delete=models.CASCADE, related_name='prices'
    )
    ticket_type = models.ForeignKey(
        TicketType, on_delete=models.PROTECT, related_name='prices'
    )
    price_pence = models.PositiveIntegerField()

    class Meta:
        ordering = ['screening', 'ticket_type']
        constraints = [
            models.UniqueConstraint(
                fields=['screening', 'ticket_type'],
                name='one_price_per_ticket_type',
            ),
        ]

    def __str__(self):
        pounds, pence = divmod(self.price_pence, 100)
        return f'{self.ticket_type}: £{pounds}.{pence:02d}'
