import pytest
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from account.services import WebSocketTicketService

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def locmem_cache():
    with override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}):
        yield
        cache.clear()


class TestWebSocketTicketView:
    def test_issues_a_ticket_redeemable_once_for_the_caller(self, api_client, user):
        response = api_client.post(reverse("ws_ticket"))

        assert response.status_code == 201
        ticket = response.data["ticket"]
        assert WebSocketTicketService().redeem(ticket) == user
        assert WebSocketTicketService().redeem(ticket) is None

    def test_requires_authentication(self):
        response = APIClient().post(reverse("ws_ticket"))

        assert response.status_code == 401
