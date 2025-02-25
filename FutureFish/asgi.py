"""
ASGI config for FutureFish project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'FutureFish.settings')

django_asgi_app = get_asgi_application()

async def application(scope, receive, send):
    if scope['type'] == 'http':
        await django_asgi_app(scope, receive, send)
    else:
        raise NotImplementedError(f"Unknown scope type {scope['type']}")
