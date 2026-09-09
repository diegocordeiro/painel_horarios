"""Context processor que injeta a base URL e o caminho de estáticos em todas as páginas.

Garante que os templates gerem URLs absolutas corretas tanto no modo de
desenvolvimento (runserver) quanto no gerador estático (render_static_site).
"""
from django.conf import settings


def site(request):
    base = settings.SITE_BASE_URL
    return {
        "base": base,
        "static_url": base + "static/",
        "site_title": "Quadro de Horários do IFPI - Campus Barras",
    }
