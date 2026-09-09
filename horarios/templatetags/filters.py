from django import template

register = template.Library()


@register.filter
def get_item(mapping, key):
    """Retorna mapping[key] ou None (para dicionários/listas)."""
    if mapping is None:
        return None
    try:
        return mapping[key]
    except (KeyError, IndexError, TypeError):
        return None


@register.filter
def get(dictionary, key):
    """Alias de get_item."""
    return get_item(dictionary, key)
