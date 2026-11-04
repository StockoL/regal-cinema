from .models import ScreeningPrice


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
