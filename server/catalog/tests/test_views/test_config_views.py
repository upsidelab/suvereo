from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth.models import Permission
from django.urls import reverse
from rest_framework import status

from account.authorization import PERMISSIONS
from agent.core.registries.embeddings.embedding_provider_registry import EmbeddingProviderRegistry
from agent.core.registries.language_models.language_model_registry import LanguageModelRegistry

pytestmark = pytest.mark.django_db


def _permission(codename: str) -> Permission:
    app_label, name = codename.split(".")
    return Permission.objects.get(codename=name, content_type__app_label=app_label)


class TestConfigView:
    @pytest.fixture
    def url(self):
        return reverse("config")

    def test_outsider_is_denied(self, api_client, url):
        response = api_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch.object(LanguageModelRegistry, "get_provider_classes", return_value=[])
    @patch.object(EmbeddingProviderRegistry, "get_provider_classes", return_value=[])
    def test_add_dataset_holder_is_allowed(self, _mock_embedding, _mock_language, api_client, user, url):
        user.user_permissions.add(_permission(PERMISSIONS.DATASET.ADD))

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK

    @patch.object(LanguageModelRegistry, "get_provider_classes", return_value=[])
    @patch.object(EmbeddingProviderRegistry, "get_provider_classes", return_value=[])
    def test_change_dataset_holder_is_allowed(self, _mock_embedding, _mock_language, api_client, user, url):
        user.user_permissions.add(_permission(PERMISSIONS.DATASET.CHANGE))

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK

    @patch.object(LanguageModelRegistry, "get_provider_classes", return_value=[])
    @patch.object(EmbeddingProviderRegistry, "get_provider_classes", return_value=[])
    def test_admin_is_allowed(self, _mock_embedding, _mock_language, admin_api_client, url):
        response = admin_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK


class TestConfigLanguageModelView:
    @pytest.fixture
    def url(self):
        return reverse("config_language_model_provider", kwargs={"provider_name": "OpenAI"})

    def test_outsider_is_denied(self, api_client, url):
        response = api_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch.object(LanguageModelRegistry, "provider_class_by_name")
    def test_add_dataset_holder_is_allowed(self, mock_provider_class_by_name, api_client, user, url):
        user.user_permissions.add(_permission(PERMISSIONS.DATASET.ADD))
        mock_provider = MagicMock()
        mock_provider.available_models.return_value = ["gpt-4o"]
        mock_provider_class_by_name.return_value = mock_provider

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data == ["gpt-4o"]

    @patch.object(LanguageModelRegistry, "provider_class_by_name")
    def test_change_dataset_holder_is_allowed(self, mock_provider_class_by_name, api_client, user, url):
        user.user_permissions.add(_permission(PERMISSIONS.DATASET.CHANGE))
        mock_provider = MagicMock()
        mock_provider.available_models.return_value = []
        mock_provider_class_by_name.return_value = mock_provider

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK

    @patch.object(LanguageModelRegistry, "provider_class_by_name")
    def test_admin_is_allowed(self, mock_provider_class_by_name, admin_api_client, url):
        mock_provider = MagicMock()
        mock_provider.available_models.return_value = []
        mock_provider_class_by_name.return_value = mock_provider

        response = admin_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK


class TestConfigEmbeddingModelView:
    @pytest.fixture
    def url(self):
        return reverse("config_embedding_provider", kwargs={"provider_name": "OpenAI"})

    def test_outsider_is_denied(self, api_client, url):
        response = api_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch.object(EmbeddingProviderRegistry, "provider_class_by_name")
    def test_add_dataset_holder_is_allowed(self, mock_provider_class_by_name, api_client, user, url):
        user.user_permissions.add(_permission(PERMISSIONS.DATASET.ADD))
        mock_provider = MagicMock()
        mock_provider.available_models.return_value = ["text-embedding-3-large"]
        mock_provider.vector_size_constraints.return_value = {}
        mock_provider_class_by_name.return_value = mock_provider

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["models"] == ["text-embedding-3-large"]

    @patch.object(EmbeddingProviderRegistry, "provider_class_by_name")
    def test_change_dataset_holder_is_allowed(self, mock_provider_class_by_name, api_client, user, url):
        user.user_permissions.add(_permission(PERMISSIONS.DATASET.CHANGE))
        mock_provider = MagicMock()
        mock_provider.available_models.return_value = []
        mock_provider.vector_size_constraints.return_value = {}
        mock_provider_class_by_name.return_value = mock_provider

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK

    @patch.object(EmbeddingProviderRegistry, "provider_class_by_name")
    def test_admin_is_allowed(self, mock_provider_class_by_name, admin_api_client, url):
        mock_provider = MagicMock()
        mock_provider.available_models.return_value = []
        mock_provider.vector_size_constraints.return_value = {}
        mock_provider_class_by_name.return_value = mock_provider

        response = admin_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
