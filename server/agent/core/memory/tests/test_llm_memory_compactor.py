from unittest.mock import MagicMock

import pytest
from django.contrib.auth import get_user_model
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from model_bakery import baker

from agent.core.memory.llm_memory_compactor import TOOL_RESULT_MAX_CHARACTERS, LLMMemoryCompactor
from agent.core.memory.persistent_chat_history import PersistentChatHistory
from agent.core.repositories import DjangoConversationRepository
from agent.models import Agent, Conversation
from catalog.models import DataSet


@pytest.fixture
def conversation():
    user = baker.make(get_user_model())
    data_set = baker.make(DataSet)
    agent = baker.make(Agent, dataset=data_set)
    return baker.make(Conversation, user=user, data_set=data_set, agent=agent)


@pytest.fixture
def llm():
    mock = MagicMock()
    mock.invoke.return_value = AIMessage(content="This is a summary.")
    return mock


TOKEN_LIMIT = 300  # a turn of two 100-character messages is about 56 tokens, the verbatim budget about 90


@pytest.fixture
def chat_history(conversation):
    return PersistentChatHistory(DjangoConversationRepository(Conversation), conversation.id)


@pytest.fixture
def compactor(conversation, llm, chat_history):
    return LLMMemoryCompactor(
        conversation_repo=DjangoConversationRepository(Conversation),
        conversation_id=conversation.id,
        llm=llm,
        chat_history=chat_history,
        token_limit=TOKEN_LIMIT,
    )


def _add_turns(chat_history, count: int, start: int = 0) -> None:
    for index in range(start, start + count):
        chat_history.add_message(HumanMessage(content=f"question {index:03} " + "q" * 88))
        chat_history.add_message(AIMessage(content=f"answer {index:03} " + "a" * 90))


def _window_texts(chat_history) -> list[str]:
    return [" ".join(message.text.split()[:2]) for message in chat_history.messages]


@pytest.mark.django_db
class TestLLMMemoryCompactorGetSummary:
    def test_returns_none_when_no_summary_exists(self, compactor):
        assert compactor.get_summary() is None

    def test_returns_stored_summary(self, conversation, compactor):
        conversation.conversation_summary = "Existing summary."
        conversation.save()

        assert LLMMemoryCompactor(
            conversation_repo=DjangoConversationRepository(Conversation),
            conversation_id=conversation.id,
            llm=MagicMock(),
            chat_history=MagicMock(),
            token_limit=TOKEN_LIMIT,
        ).get_summary() == "Existing summary."


@pytest.mark.django_db
class TestLLMMemoryCompactorCompactIfNeeded:
    def test_does_not_compact_below_limit(self, conversation, compactor, llm, chat_history):
        _add_turns(chat_history, 3)

        compactor.compact_if_needed()

        conversation.refresh_from_db()
        assert conversation.conversation_summary is None
        llm.invoke.assert_not_called()
        assert len(chat_history.messages) == 6

    def test_compacts_all_but_the_most_recent_turn_above_limit(self, conversation, compactor, llm, chat_history):
        _add_turns(chat_history, 6)

        compactor.compact_if_needed()

        conversation.refresh_from_db()
        assert conversation.conversation_summary == "This is a summary."
        llm.invoke.assert_called_once()
        assert _window_texts(chat_history) == ["question 005", "answer 005"]

    def test_summary_and_window_do_not_overlap(self, compactor, llm, chat_history):
        _add_turns(chat_history, 6)

        compactor.compact_if_needed()

        summarized = llm.invoke.call_args[0][0][1].content
        assert "question 004" in summarized
        assert "question 005" not in summarized
        assert "question 004" not in "".join(_window_texts(chat_history))

    def test_window_starts_on_a_human_message(self, compactor, chat_history):
        _add_turns(chat_history, 5)
        chat_history.add_message(HumanMessage(content="Find shoes " + "q" * 80))
        chat_history.add_messages(
            [
                AIMessage(content="", tool_calls=[{"id": "1", "name": "search", "args": {}}]),
                ToolMessage(content="found", tool_call_id="1", name="search"),
                AIMessage(content="Here they are " + "a" * 80),
            ]
        )

        compactor.compact_if_needed()

        window = chat_history.messages
        assert isinstance(window[0], HumanMessage)
        assert [type(m) for m in window] == [HumanMessage, AIMessage, ToolMessage, AIMessage]

    def test_does_not_compact_again_until_the_window_outgrows_the_limit(
        self, conversation, compactor, llm, chat_history
    ):
        _add_turns(chat_history, 6)
        compactor.compact_if_needed()
        llm.invoke.reset_mock()

        _add_turns(chat_history, 2, start=6)
        compactor.compact_if_needed()

        llm.invoke.assert_not_called()

    def test_compacts_again_once_the_window_outgrows_the_limit(self, conversation, compactor, llm, chat_history):
        _add_turns(chat_history, 6)
        compactor.compact_if_needed()
        llm.invoke.reset_mock()

        _add_turns(chat_history, 5, start=6)
        compactor.compact_if_needed()

        llm.invoke.assert_called_once()
        request = llm.invoke.call_args[0][0][1].content
        assert "<existing_summary>\nThis is a summary.\n</existing_summary>" in request
        assert "question 005" in request
        assert "question 010" not in request
        assert _window_texts(chat_history) == ["question 010", "answer 010"]

    def test_keeps_the_latest_turn_even_when_it_exceeds_the_verbatim_budget(self, compactor, llm, chat_history):
        _add_turns(chat_history, 2)
        chat_history.add_message(HumanMessage(content="x" * 400))
        chat_history.add_message(AIMessage(content="y" * 400))

        compactor.compact_if_needed()

        assert [m.text[:1] for m in chat_history.messages] == ["x", "y"]

    def test_does_not_compact_a_window_made_of_a_single_turn(self, conversation, compactor, llm, chat_history):
        chat_history.add_message(HumanMessage(content="x" * 2000))
        chat_history.add_message(AIMessage(content="y" * 2000))

        compactor.compact_if_needed()

        llm.invoke.assert_not_called()
        assert len(chat_history.messages) == 2


@pytest.mark.django_db
class TestLLMMemoryCompactorRequest:
    def test_first_compaction_sends_transcript_as_single_human_message(self, compactor, llm, chat_history):
        _add_turns(chat_history, 6)

        compactor.compact_if_needed()

        call_args = llm.invoke.call_args[0][0]
        assert len(call_args) == 2
        assert isinstance(call_args[0], SystemMessage)
        assert isinstance(call_args[1], HumanMessage)
        assert "User: question 000" in call_args[1].content
        assert call_args[1].content.index("Assistant: answer 000") > call_args[1].content.index("User: question 000")
        assert "<existing_summary>" not in call_args[1].content

    def test_transcript_renders_tool_calls_notices_and_truncates_tool_results(self, compactor, llm, chat_history):
        _add_turns(chat_history, 3)
        chat_history.add_message(HumanMessage(content="Find shoes"))
        chat_history.add_messages(
            [
                AIMessage(content="Invoking...", tool_calls=[{"id": "1", "name": "search", "args": {}}]),
                ToolMessage(content="x" * (TOOL_RESULT_MAX_CHARACTERS + 50), tool_call_id="1", name="search"),
            ]
        )
        chat_history.add_message(SystemMessage(content="We couldn't process your request at this time"))
        _add_turns(chat_history, 2, start=3)

        compactor.compact_if_needed()

        content = llm.invoke.call_args[0][0][1].content
        assert "[Tool call: search]" in content
        assert "Invoking..." not in content
        assert "[Tool result from search: " + "x" * TOOL_RESULT_MAX_CHARACTERS + "...]" in content
        assert "x" * (TOOL_RESULT_MAX_CHARACTERS + 1) not in content
        assert "\n[Notice shown to the user: We couldn't process" in content
        assert "Assistant: [Notice" not in content
