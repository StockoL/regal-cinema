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
