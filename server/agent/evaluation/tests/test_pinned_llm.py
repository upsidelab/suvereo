from unittest.mock import MagicMock

from agent.evaluation.pinned_llm import PinnedLLM


class TestPinnedLLM:
    def test_builds_the_pinned_model_whatever_the_data_set_says(self):
        provider = MagicMock()
        registry = MagicMock()
        registry.provider_class_by_name.return_value = provider
        data_sets = MagicMock()
        data_sets.get_by_id.return_value.language_model = "gpt-4o"

        PinnedLLM.for_model("Anthropic", "claude-sonnet-5-5")(llm_registry=registry, data_set_repo=data_sets).create(1)

        registry.provider_class_by_name.assert_called_once_with("Anthropic")
        provider.assert_called_once_with("claude-sonnet-5-5")
        registry.provider_for_dataset.assert_not_called()

    def test_one_class_per_provider_and_model(self):
        assert PinnedLLM.for_model("OpenAI", "gpt-4o") is PinnedLLM.for_model("OpenAI", "gpt-4o")
        assert PinnedLLM.for_model("OpenAI", "gpt-4o") is not PinnedLLM.for_model("OpenAI", "gpt-4o-mini")
