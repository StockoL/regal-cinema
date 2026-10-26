from decimal import ROUND_HALF_UP, Decimal


def apply_discount(price_pence, percent):
    """Return a price in pence after a percentage discount.

    Worked out per ticket or item, never on a total, with the discount
    rounded to the nearest penny and halves going up (architecture
    4.10). Decimal keeps the arithmetic exact, where a float wouldn't.
    """
    percent = Decimal(str(percent))
    if not 0 <= percent <= 100:
        raise ValueError(f'A discount must be 0 to 100%, not {percent}%.')
    discount = (Decimal(price_pence) * percent / 100).quantize(
        Decimal('1'), rounding=ROUND_HALF_UP
    )
    return price_pence - int(discount)
