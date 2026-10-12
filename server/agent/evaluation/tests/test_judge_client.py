from unittest.mock import MagicMock, patch

from enthusiast_common.evaluation.suite import ModelPricing, ModelTarget
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from agent.core.registries.language_models import LanguageModelRegistry
from agent.evaluation.judge_client import EvalJudgeClient
from agent.evaluation.pricing_table import PricingTable


class TestEvalJudgeClient:
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
            judge = EvalJudgeClient(ModelTarget(provider="Anthropic", model="judge-model"), pricing)
            answer = judge.complete("grade this")

        provider.assert_called_once_with("judge-model")
        assert answer == '{"score": 1}'
        assert judge.cost().usd == 2.0
