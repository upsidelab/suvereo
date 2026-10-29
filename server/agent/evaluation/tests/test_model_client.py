from unittest.mock import MagicMock, patch

import pytest
from enthusiast_common.evaluation.chat_message import ChatMessage
from enthusiast_common.evaluation.suite import ModelPricing, ModelTarget
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from agent.core.registries.language_models import LanguageModelRegistry
from agent.evaluation.model_client import EvalModelClient
from agent.evaluation.pricing_table import PricingTable


class TestEvalModelClient:
    def test_answers_and_tallies_its_own_cost(self):
        reply = AIMessage(
            content='{"score": 1}',
            usage_metadata={"input_tokens": 1_000_000, "output_tokens": 0, "total_tokens": 1_000_000},
            response_metadata={"model_name": "judge-model"},
        )
        provider = MagicMock()
        provider.return_value.provide_language_model.side_effect = lambda callbacks: GenericFakeChatModel(
            messages=iter([reply]), callbacks=callbacks
        )
        pricing = PricingTable({"judge-model": ModelPricing(input_per_million=2, output_per_million=8)})

        with patch.object(LanguageModelRegistry, "provider_class_by_name", return_value=provider):
            judge = EvalModelClient(ModelTarget(provider="Anthropic", model="judge-model"), pricing)
            answer = judge.complete("grade this")

        provider.assert_called_once_with("judge-model")
        assert answer == '{"score": 1}'
        assert judge.cost().usd == 2.0

    def test_a_chat_goes_to_the_model_as_its_system_prompt_and_messages_in_order(self):
        provider = MagicMock()
        llm = provider.return_value.provide_language_model.return_value
        llm.invoke.return_value.text = "Under 50 EUR"
        messages = [ChatMessage(role="user", text="Hi"), ChatMessage(role="assistant", text="Budget?")]

        with patch.object(LanguageModelRegistry, "provider_class_by_name", return_value=provider):
            client = EvalModelClient(ModelTarget(provider="OpenAI", model="user-model"), PricingTable({}))
            answer = client.chat(messages, "Play a user")

        sent = llm.invoke.call_args.args[0]
        assert answer == "Under 50 EUR"
        assert [(type(m), m.content) for m in sent] == [
            (SystemMessage, "Play a user"),
            (HumanMessage, "Hi"),
            (AIMessage, "Budget?"),
        ]

    def test_a_call_can_ask_another_model_priced_by_its_own_pricing(self):
        def reply(model):
            return AIMessage(
                content=model,
                usage_metadata={"input_tokens": 1_000_000, "output_tokens": 0, "total_tokens": 1_000_000},
                response_metadata={"model_name": model},
            )

        provider = MagicMock()
        provider.return_value.provide_language_model.side_effect = lambda callbacks: GenericFakeChatModel(
            messages=iter([reply(provider.call_args.args[0])] * 2), callbacks=callbacks
        )
        pricing = PricingTable(
            {
                "judge-model": ModelPricing(input_per_million=2, output_per_million=8),
            }
        )

        with patch.object(LanguageModelRegistry, "provider_class_by_name", return_value=provider):
            judge = EvalModelClient(ModelTarget(provider="OpenAI", model="judge-model"), pricing)
            strong = ModelTarget(
                provider="OpenAI",
                model="strong-model",
                pricing=ModelPricing(input_per_million=10, output_per_million=40),
            )
            answers = [judge.complete("a"), judge.complete("b", strong), judge.complete("c", strong)]

        assert answers == ["judge-model", "strong-model", "strong-model"]
        assert provider.call_count == 2
        assert judge.cost().usd == 22.0

    def test_without_any_model_asking_fails(self):
        with pytest.raises(ValueError, match="No model to ask"):
            EvalModelClient(None, PricingTable({})).complete("grade this")
