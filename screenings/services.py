from django.core.cache import cache
from django.db.models import Q

from .models import ScreeningPrice, Seat, SeatingLayout


def fill_prices(screening):
    """Give a screening a price for each ticket type its film can be
    booked with, starting from the ticket class's default. Companion
    tickets are free. A price already set is left alone, so staff
    adjust any line afterwards (architecture 4.1)."""
    default = screening.ticket_class.default_price_pence
    already_priced = screening.prices.values('ticket_type')
    for ticket_type in screening.film.ticket_types().exclude(
            pk__in=already_priced):
        if ticket_type.is_companion:
            price = 0
        elif default is None:
            continue
        else:
            price = default
        ScreeningPrice.objects.create(
            screening=screening, ticket_type=ticket_type, price_pence=price,
        )


# Each of Render's workers has its own cache, and a change clears only
# the one that made it, so a copy never lasts longer than this (4.34).
LAYOUT_CACHE_SECONDS = 60


def layout_cache_key(screen_id, layout_id):
    return f'seat-layout:{screen_id}:{layout_id}'


def layout_seats(screen_id, layout_id):
    """A screen's fixed seats plus one layout's, in use, in grid order:
    the shape of the room, which rarely changes. Cached per layout and
    cleared whenever a seat or layout of the screen changes. Who holds
    or has bought a seat is never cached (4.33)."""
    key = layout_cache_key(screen_id, layout_id)
    seats = cache.get(key)
    if seats is None:
        seats = list(Seat.objects.filter(
            Q(layout__isnull=True) | Q(layout=layout_id),
            screen=screen_id, is_active=True,
        ).order_by('row_index', 'column_index'))
        cache.set(key, seats, LAYOUT_CACHE_SECONDS)
    return seats


def clear_layout_seats(screen_id):
    """Forget every cached layout of a screen. A fixed seat belongs to
    all of them, so any change clears the lot."""
    layouts = SeatingLayout.objects.filter(screen=screen_id)
    cache.delete_many([
        layout_cache_key(screen_id, layout_id)
        for layout_id in layouts.values_list('pk', flat=True)
    ])
