from unittest.mock import patch

import pytest
from django.core.cache import caches
from django.urls import reverse
from rest_framework import status

from catalog.integrations import oauth_config, oauth_flows
from catalog.integrations.oauth_views import callback_uri
from catalog.integrations.registry import IntegrationPluginRegistry
from catalog.tests.integration_mocks import MockOAuthIntegration, MockSingleInstanceIntegration

pytestmark = pytest.mark.django_db

ORIGIN = "https://app.example.com"


@pytest.fixture(autouse=True)
def _isolated_flows(settings):
    """Keep flows local to the test run, so the suite needs no Redis of its own."""
    settings.CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
    caches["default"].clear()
    yield
    caches["default"].clear()


@pytest.fixture(autouse=True)
def _trusted_origin(settings):
    settings.CORS_ALLOWED_ORIGINS = [ORIGIN]


class TestIntegrationOAuthStartView:
    @pytest.fixture
    def url(self, data_set):
        return reverse("integration-oauth-start", kwargs={"data_set_id": data_set.pk})

    def test_post_unknown_type_returns_400(self, admin_api_client, url):
        response = admin_api_client.post(url, {"type": "does_not_exist", "config": {}}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert oauth_flows.pop("state-123") is None

    @patch.object(IntegrationPluginRegistry, "get_plugin_class_by_type")
    def test_post_type_without_oauth_support_returns_400(self, mock_get_plugin_class, admin_api_client, url):
        mock_get_plugin_class.return_value = MockSingleInstanceIntegration

        response = admin_api_client.post(url, {"type": "mock_single", "config": {}}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert oauth_flows.pop("state-123") is None

    @patch.object(IntegrationPluginRegistry, "get_plugin_class_by_type")
    def test_post_returns_the_authorization_url_and_stores_the_flow(self, mock_get_plugin_class, admin_api_client, url):
        mock_get_plugin_class.return_value = MockOAuthIntegration

        response = admin_api_client.post(
            url, {"type": "mock_oauth", "config": {}}, format="json", HTTP_ORIGIN=ORIGIN
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["authorization_url"].startswith("https://provider.example.com/authorize")
        assert response.data["expires_in"] == oauth_config.FLOW_LIFETIME_SECONDS
        flow = oauth_flows.pop("state-123")
        assert flow["integration_type"] == "mock_oauth"
        assert flow["origin"] == ORIGIN

    @patch.object(IntegrationPluginRegistry, "get_plugin_class_by_type")
    def test_post_from_an_untrusted_origin_stores_no_origin_to_return_to(
        self, mock_get_plugin_class, admin_api_client, url
    ):
        """A credential is only ever handed back to an origin already trusted for browser calls."""
        mock_get_plugin_class.return_value = MockOAuthIntegration

        admin_api_client.post(
            url, {"type": "mock_oauth", "config": {}}, format="json", HTTP_ORIGIN="https://evil.example.com"
        )

        assert oauth_flows.pop("state-123")["origin"] == ""

    @patch.object(IntegrationPluginRegistry, "get_plugin_class_by_type")
    def test_post_reports_a_provider_failure_as_a_message(self, mock_get_plugin_class, admin_api_client, url):
        """A server that cannot be connected to is the admin's problem to read, not a 500."""
        mock_get_plugin_class.return_value = MockOAuthIntegration

        with patch.object(MockOAuthIntegration, "oauth_start", side_effect=RuntimeError("no metadata")):
            response = admin_api_client.post(url, {"type": "mock_oauth", "config": {}}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "no metadata" in response.data["detail"]
        assert oauth_flows.pop("state-123") is None

    @patch.object(IntegrationPluginRegistry, "get_plugin_class_by_type")
    def test_post_by_a_user_without_the_permission_starts_no_flow(self, mock_get_plugin_class, api_client, url):
        """Starting a flow registers a client with a third party, so it needs the same right as adding one."""
        mock_get_plugin_class.return_value = MockOAuthIntegration

        response = api_client.post(url, {"type": "mock_oauth", "config": {}}, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert oauth_flows.pop("state-123") is None


class TestClientRegistrationIsReused:
    """Each registration leaves a record with the provider, so pressing Connect twice must not make two."""

    @pytest.fixture
    def url(self, data_set):
        return reverse("integration-oauth-start", kwargs={"data_set_id": data_set.pk})

    @patch.object(IntegrationPluginRegistry, "get_plugin_class_by_type")
    def test_a_second_connect_reuses_the_first_registration(self, mock_get_plugin_class, admin_api_client, url):
        mock_get_plugin_class.return_value = MockOAuthIntegration

        with patch.object(MockOAuthIntegration, "oauth_start", wraps=MockOAuthIntegration.oauth_start) as spy:
            admin_api_client.post(url, {"type": "mock_oauth", "config": {}}, format="json")
            admin_api_client.post(url, {"type": "mock_oauth", "config": {}}, format="json")

        assert spy.call_args_list[0].args[2] is None
        assert spy.call_args_list[1].args[2] == {"client_id": "registered-once"}

    @patch.object(IntegrationPluginRegistry, "get_plugin_class_by_type")
    def test_a_failed_start_keeps_the_registration(self, mock_get_plugin_class, admin_api_client, url):
        """Starting never exercises the registration, so a failure there says nothing about it."""
        mock_get_plugin_class.return_value = MockOAuthIntegration
        admin_api_client.post(url, {"type": "mock_oauth", "config": {}}, format="json")

        with patch.object(MockOAuthIntegration, "oauth_start", side_effect=RuntimeError("network blip")):
            admin_api_client.post(url, {"type": "mock_oauth", "config": {}}, format="json")

        with patch.object(MockOAuthIntegration, "oauth_start", wraps=MockOAuthIntegration.oauth_start) as spy:
            admin_api_client.post(url, {"type": "mock_oauth", "config": {}}, format="json")

        assert spy.call_args_list[0].args[2] == {"client_id": "registered-once"}

    @patch.object(IntegrationPluginRegistry, "get_plugin_class_by_type")
    def test_a_registration_carrying_a_secret_is_not_kept(self, mock_get_plugin_class, admin_api_client, url):
        """We register as a public client; a secret coming back is a credential, not cache content."""
        mock_get_plugin_class.return_value = MockOAuthIntegration
        confidential = ("https://provider.example.com/authorize", {
            "state": "state-123",
            "client": {"client_id": "abc", "client_secret": "s3cret"},
        })

        with patch.object(MockOAuthIntegration, "oauth_start", return_value=confidential):
            admin_api_client.post(url, {"type": "mock_oauth", "config": {}}, format="json")

        with patch.object(MockOAuthIntegration, "oauth_start", wraps=MockOAuthIntegration.oauth_start) as spy:
            admin_api_client.post(url, {"type": "mock_oauth", "config": {}}, format="json")

        assert spy.call_args_list[0].args[2] is None


class TestCallbackUri:
    """The redirect URI must match across registration, authorize and exchange, or providers refuse it."""

    def test_it_is_derived_from_the_request_when_nothing_is_configured(self, rf):
        with patch.object(oauth_config, "BASE_URL", ""):
            assert callback_uri(rf.post("/x", HTTP_HOST="localhost:8001")) == (
                "http://localhost:8001/api/integrations/oauth/callback/"
            )

    def test_a_configured_base_url_wins_over_what_the_request_reports(self, rf):
        """Behind TLS termination the request says http, which would not match what was registered."""
        with patch.object(oauth_config, "BASE_URL", "https://api.example.com"):
            assert callback_uri(rf.post("/x", HTTP_HOST="localhost:8001")) == (
                "https://api.example.com/api/integrations/oauth/callback/"
            )

    def test_a_trailing_slash_does_not_double_up(self, rf):
        with patch.object(oauth_config, "BASE_URL", "https://api.example.com/"):
            assert "//api/" not in callback_uri(rf.post("/x", HTTP_HOST="localhost:8001"))


class TestIntegrationOAuthCallbackView:
    @pytest.fixture
    def url(self):
        return reverse("integration-oauth-callback")

    @pytest.fixture
    def start_url(self, data_set):
        return reverse("integration-oauth-start", kwargs={"data_set_id": data_set.pk})

    @pytest.fixture
    def flow(self, admin_user):
        oauth_flows.store(
            "state-123",
            {
                "integration_type": "mock_oauth",
                "pending": {"state": "state-123", "redirect_uri": "http://testserver/callback"},
                "origin": ORIGIN,
                "user_id": admin_user.pk,
            },
        )

    @patch.object(IntegrationPluginRegistry, "get_plugin_class_by_type")
    def test_get_exchanges_the_code_and_keeps_the_config_for_collection(
        self, mock_get_plugin_class, client, url, flow
    ):
        mock_get_plugin_class.return_value = MockOAuthIntegration

        client.get(url, {"state": "state-123", "code": "abc"})

        assert oauth_flows.read_result("state-123")["config"]["auth_token"] == "Bearer token-for-abc"

    @patch.object(IntegrationPluginRegistry, "get_plugin_class_by_type")
    def test_get_hands_the_popup_back_to_the_origin_that_began_the_flow(
        self, mock_get_plugin_class, client, url, flow
    ):
        mock_get_plugin_class.return_value = MockOAuthIntegration

        response = client.get(url, {"state": "state-123", "code": "abc"})

        assert response.status_code == status.HTTP_302_FOUND
        assert response["Location"].startswith(f"{ORIGIN}/oauth/complete")

    @patch.object(IntegrationPluginRegistry, "get_plugin_class_by_type")
    def test_the_credential_never_travels_in_the_redirect_url(self, mock_get_plugin_class, client, url, flow):
        """Only the state goes in the URL; a token there would be kept in browser history."""
        mock_get_plugin_class.return_value = MockOAuthIntegration

        response = client.get(url, {"state": "state-123", "code": "abc"})

        assert "token-for-abc" not in response["Location"]

    @patch.object(IntegrationPluginRegistry, "get_plugin_class_by_type")
    def test_an_untrusted_origin_gets_a_page_rather_than_a_redirect(self, mock_get_plugin_class, client, url):
        mock_get_plugin_class.return_value = MockOAuthIntegration
        oauth_flows.store(
            "state-456",
            {"integration_type": "mock_oauth", "pending": {}, "origin": "", "user_id": 1},
        )

        response = client.get(url, {"state": "state-456", "code": "abc"})

        assert response.status_code == status.HTTP_200_OK
        assert "Could not return to the app" in response.content.decode()

    @patch.object(IntegrationPluginRegistry, "get_plugin_class_by_type")
    def test_get_consumes_the_flow_so_a_code_cannot_be_replayed(self, mock_get_plugin_class, client, url, flow):
        mock_get_plugin_class.return_value = MockOAuthIntegration

        client.get(url, {"state": "state-123", "code": "abc"})
        second = client.get(url, {"state": "state-123", "code": "abc"})

        assert "expired or was never started" in second.content.decode()

    def test_get_unknown_state_reports_an_error_without_failing(self, client, url):
        response = client.get(url, {"state": "never-issued", "code": "abc"})

        assert response.status_code == status.HTTP_200_OK
        assert "expired or was never started" in response.content.decode()

    @patch.object(IntegrationPluginRegistry, "get_plugin_class_by_type")
    def test_a_rejected_client_is_forgotten_so_the_next_attempt_registers_again(
        self, mock_get_plugin_class, client, url, start_url, admin_api_client
    ):
        mock_get_plugin_class.return_value = MockOAuthIntegration
        admin_api_client.post(start_url, {"type": "mock_oauth", "config": {}}, format="json")

        client.get(url, {"state": "state-123", "error": "invalid_client"})

        with patch.object(MockOAuthIntegration, "oauth_start", wraps=MockOAuthIntegration.oauth_start) as spy:
            admin_api_client.post(start_url, {"type": "mock_oauth", "config": {}}, format="json")

        assert spy.call_args_list[0].args[2] is None

    @patch.object(IntegrationPluginRegistry, "get_plugin_class_by_type")
    def test_a_person_declining_leaves_the_registration_alone(
        self, mock_get_plugin_class, client, url, start_url, admin_api_client
    ):
        """Refusing consent says nothing about the client, and re-registering would be wasted."""
        mock_get_plugin_class.return_value = MockOAuthIntegration
        admin_api_client.post(start_url, {"type": "mock_oauth", "config": {}}, format="json")

        client.get(url, {"state": "state-123", "error": "access_denied"})

        with patch.object(MockOAuthIntegration, "oauth_start", wraps=MockOAuthIntegration.oauth_start) as spy:
            admin_api_client.post(start_url, {"type": "mock_oauth", "config": {}}, format="json")

        assert spy.call_args_list[0].args[2] == {"client_id": "registered-once"}

    def test_a_provider_refusal_is_kept_for_the_form_to_report(self, client, url, flow):
        client.get(url, {"state": "state-123", "error": "access_denied", "error_description": "User said no"})

        assert oauth_flows.read_result("state-123")["error"] == "User said no"

    @patch.object(IntegrationPluginRegistry, "get_plugin_class_by_type")
    def test_a_callback_without_a_code_is_kept_as_an_error(self, mock_get_plugin_class, client, url, flow):
        mock_get_plugin_class.return_value = MockOAuthIntegration

        client.get(url, {"state": "state-123"})

        assert "no authorization code" in oauth_flows.read_result("state-123")["error"]

    def test_get_needs_no_authentication(self, client, url):
        """The provider redirects the admin's browser here with no token of ours attached."""
        response = client.get(url, {"state": "never-issued", "code": "abc"})

        assert response.status_code == status.HTTP_200_OK


class TestIntegrationOAuthResultView:
    @pytest.fixture
    def url(self):
        return reverse("integration-oauth-result")

    @pytest.fixture
    def callback_url(self):
        return reverse("integration-oauth-callback")

    @pytest.fixture
    def flow(self, admin_user):
        oauth_flows.store(
            "state-123",
            {
                "integration_type": "mock_oauth",
                "pending": {"state": "state-123"},
                "origin": ORIGIN,
                "user_id": admin_user.pk,
            },
        )

    def test_get_before_the_callback_is_pending(self, admin_api_client, url, flow):
        response = admin_api_client.get(url, {"state": "state-123"})

        assert response.data["status"] == "pending"

    @patch.object(IntegrationPluginRegistry, "get_plugin_class_by_type")
    def test_get_after_the_callback_returns_the_config(
        self, mock_get_plugin_class, admin_api_client, client, url, callback_url, flow
    ):
        mock_get_plugin_class.return_value = MockOAuthIntegration
        client.get(callback_url, {"state": "state-123", "code": "abc"})

        response = admin_api_client.get(url, {"state": "state-123"})

        assert response.data["status"] == "ready"
        assert response.data["config"]["auth_token"] == "Bearer token-for-abc"

    @patch.object(IntegrationPluginRegistry, "get_plugin_class_by_type")
    def test_a_result_is_collected_once(self, mock_get_plugin_class, admin_api_client, client, url, callback_url, flow):
        mock_get_plugin_class.return_value = MockOAuthIntegration
        client.get(callback_url, {"state": "state-123", "code": "abc"})

        admin_api_client.get(url, {"state": "state-123"})
        second = admin_api_client.get(url, {"state": "state-123"})

        assert second.data["status"] == "pending"

    @patch.object(IntegrationPluginRegistry, "get_plugin_class_by_type")
    def test_another_user_cannot_collect_someone_elses_token(
        self, mock_get_plugin_class, api_client, client, url, callback_url, flow
    ):
        """The result carries a credential, so only the account that began the flow may take it."""
        mock_get_plugin_class.return_value = MockOAuthIntegration
        client.get(callback_url, {"state": "state-123", "code": "abc"})

        response = api_client.get(url, {"state": "state-123"})

        assert response.data["status"] == "pending"
        assert "config" not in response.data or response.data.get("config") is None

    @patch.object(IntegrationPluginRegistry, "get_plugin_class_by_type")
    def test_another_user_asking_does_not_destroy_the_result(
        self, mock_get_plugin_class, api_client, admin_api_client, client, url, callback_url, flow
    ):
        """Consuming on a failed ownership check would let anyone strand the rightful owner."""
        mock_get_plugin_class.return_value = MockOAuthIntegration
        client.get(callback_url, {"state": "state-123", "code": "abc"})

        api_client.get(url, {"state": "state-123"})
        owner = admin_api_client.get(url, {"state": "state-123"})

        assert owner.data["status"] == "ready"
        assert owner.data["config"]["auth_token"] == "Bearer token-for-abc"

    def test_get_requires_a_known_state(self, admin_api_client, url):
        response = admin_api_client.get(url, {"state": "never-issued"})

        assert response.data["status"] == "pending"