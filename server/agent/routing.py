from django.conf import settings
from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(r"ws/chat/(?P<conversation_id>\d+)/$", consumers.ChatConsumer.as_asgi()),
]


def get_websocket_trusted_origins():
    """ALLOWED_HOSTS entries usable as WebSocket origin patterns, plus CORS_ALLOWED_ORIGINS.

    Excludes a literal "*" from ALLOWED_HOSTS: Django treats it as "any host" for its
    own Host-header check, but channels' OriginValidator treats "*" as "allow any
    origin" too - including it here would silently disable WebSocket origin validation.
    """
    return [host for host in settings.ALLOWED_HOSTS if host != "*"] + settings.CORS_ALLOWED_ORIGINS
