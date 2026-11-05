"""
ASGI config for pecl project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pecl.settings")
django_asgi_app = get_asgi_application()
ENABLE_WEBSOCKETS = os.environ.get("ENABLE_WEBSOCKETS", "true").lower() == "true"

if ENABLE_WEBSOCKETS:
    from channels.routing import ProtocolTypeRouter, URLRouter
    from channels.security.websocket import OriginValidator
    from django.conf import settings

    import agent.routing
    from agent.ws_auth import TicketAuthMiddleware

    application = ProtocolTypeRouter(
        {
            "http": django_asgi_app,
            "websocket": OriginValidator(
                TicketAuthMiddleware(URLRouter(agent.routing.websocket_urlpatterns)),
                settings.CORS_ALLOWED_ORIGINS,
            ),
        }
    )
else:
    application = django_asgi_app
