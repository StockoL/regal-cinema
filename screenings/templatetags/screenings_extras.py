from django import template

register = template.Library()


@register.filter
def runtime(minutes):
    """132 minutes reads as "2 hours 12 minutes"."""
    hours, minutes = divmod(int(minutes), 60)
    parts = []
    if hours:
        parts.append(f'{hours} hour{"s" if hours != 1 else ""}')
    if minutes or not hours:
        parts.append(f'{minutes} minute{"s" if minutes != 1 else ""}')
    return ' '.join(parts)


@register.filter
def pounds(pence):
    """650 pence reads as "£6.50". Money is always whole pence."""
    whole, rest = divmod(int(pence), 100)
    return f'£{whole}.{rest:02d}'


@register.filter
def get_item(mapping, key):
    """Look a key up in a dict from a template."""
    return mapping.get(key, '')
