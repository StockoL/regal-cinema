"""The rules a basket must meet before checkout (architecture 4.2).

They read the ticket types' flags, never their names, so a venue can
add its own types in the admin. Nothing here touches the database.
"""


class BasketError(Exception):
    """A basket that can't go to checkout. The message is written for
    the customer."""


def check_basket(film, ticket_types, infants=0):
    """Raise BasketError if the basket breaks a rule. ticket_types has
    one entry per seat."""
    if not ticket_types:
        raise BasketError('Choose at least one seat.')

    if infants and not film.allows_infants:
        raise BasketError(
            "Under 2s can't come to this film. They're only admitted to "
            'U, PG and 12A films.'
        )

    # A ticket that can look after a child or an infant.
    independent = [t for t in ticket_types if not t.requires_adult]
    needs_an_adult = infants or any(t.requires_adult for t in ticket_types)
    if needs_an_adult and not independent:
        raise BasketError(
            'Children and under 2s must come with someone on another '
            'ticket type, such as Adult.'
        )

    # A Companion comes with someone on a full-price ticket, one each.
    companions = sum(t.is_companion for t in ticket_types)
    full_price = sum(not t.is_companion for t in independent)
    if companions > full_price:
        raise BasketError(
            'Each Companion ticket comes with someone on a full-price '
            'ticket in the same booking, one Companion each.'
        )
