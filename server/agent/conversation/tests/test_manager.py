from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from model_bakery import baker

from agent.conversation.manager import ConversationManager
from agent.core.registries.agents.agent_registry import AgentRegistry
from agent.models import Agent, Conversation, Message
from catalog.integrations.resolver import IntegrationPluginResolver
from catalog.models import DataSet


@pytest.mark.django_db
class TestConversationManager:
    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.manager = ConversationManager()
        self.user = baker.make(get_user_model())
        self.data_set = baker.make(DataSet)
        self.agent = baker.make(Agent, dataset=self.data_set)

    def test_create_conversation_success(self):
        """Test successful conversation creation."""
        # Given
        user_id = self.user.id

        # When
        conversation = self.manager.create_conversation(user_id=user_id, agent_id=self.agent.id)

        # Then
        assert conversation is not None
        assert conversation.user == self.user
        assert conversation.data_set == self.data_set
        assert conversation.started_at is not None
        assert conversation.summary is None
        assert Conversation.objects.filter(id=conversation.id).exists()

    def test_create_conversation_with_invalid_user_id(self):
        """Test conversation creation with invalid user ID."""
        # Given
        invalid_user_id = 99999

        # When & Then
        with pytest.raises(ObjectDoesNotExist):
            self.manager.create_conversation(user_id=invalid_user_id, agent_id=self.agent.id)

    def test_create_conversation_with_invalid_agent_id(self):
        """Test conversation creation with invalid agent configuration ID."""
        # Given
        user_id = self.user.id
        invalid_agent_id = 99999

        # When & Then
        with pytest.raises(Agent.DoesNotExist):
            self.manager.create_conversation(user_id=user_id, agent_id=invalid_agent_id)

    def test_get_conversation_success(self):
        """Test successful conversation retrieval."""
        # Given
        conversation = Conversation.objects.create(
            user=self.user,
            data_set=self.data_set,
            started_at=datetime.now(),
            agent=self.agent,
        )
        user_id = self.user.id
        data_set_id = self.data_set.id
        conversation_id = conversation.id

        # When
        retrieved_conversation = self.manager.get_conversation(
            user_id=user_id, data_set_id=data_set_id, conversation_id=conversation_id
        )

        # Then
        assert retrieved_conversation == conversation
        assert retrieved_conversation.user == self.user
        assert retrieved_conversation.data_set == self.data_set

    def test_get_conversation_with_invalid_user_id(self):
        """Test conversation retrieval with invalid user ID."""
        # Given
        conversation = Conversation.objects.create(
            user=self.user,
            data_set=self.data_set,
            started_at=datetime.now(),
            agent=self.agent,
        )
        invalid_user_id = 99999
        data_set_id = self.data_set.id
        conversation_id = conversation.id

        # When & Then
        with pytest.raises(ObjectDoesNotExist):
            self.manager.get_conversation(
                user_id=invalid_user_id, data_set_id=data_set_id, conversation_id=conversation_id
            )

    def test_get_conversation_with_invalid_data_set_id(self):
        """Test conversation retrieval with invalid data set ID."""
        # Given
        conversation = Conversation.objects.create(
            user=self.user,
            data_set=self.data_set,
            started_at=datetime.now(),
            agent=self.agent,
        )
        user_id = self.user.id
        invalid_data_set_id = 99999
        conversation_id = conversation.id

        # When & Then
        with pytest.raises(ObjectDoesNotExist):
            self.manager.get_conversation(
                user_id=user_id, data_set_id=invalid_data_set_id, conversation_id=conversation_id
            )

    def test_get_conversation_with_invalid_conversation_id(self):
        """Test conversation retrieval with invalid conversation ID."""
        # Given
        user_id = self.user.id
        data_set_id = self.data_set.id
        invalid_conversation_id = 99999

        # When & Then
        with pytest.raises(ObjectDoesNotExist):
            self.manager.get_conversation(
                user_id=user_id, data_set_id=data_set_id, conversation_id=invalid_conversation_id
            )

    def test_get_conversation_with_wrong_user_ownership(self):
        """Test conversation retrieval with conversation owned by different user."""
        # Given
        other_user = get_user_model().objects.create_user(email="other@example.com", password="testpass123")
        other_data_set = DataSet.objects.create(name="Other DataSet")

        conversation = Conversation.objects.create(
            user=other_user,
            data_set=other_data_set,
            started_at=datetime.now(),
            agent=self.agent,
        )
        user_id = self.user.id
        data_set_id = self.data_set.id
        conversation_id = conversation.id

        # When & Then
        with pytest.raises(ObjectDoesNotExist):
            self.manager.get_conversation(user_id=user_id, data_set_id=data_set_id, conversation_id=conversation_id)

    @patch("agent.conversation.manager.ConversationManager.get_answer")
    def test_respond_to_user_message_first_message_sets_summary(self, mock_get_answer):
        """Test that first message sets conversation summary."""
        # Given
        conversation = Conversation.objects.create(
            user=self.user,
            data_set=self.data_set,
            started_at=datetime.now(),
            agent=self.agent,
        )
        user_id = self.user.id
        data_set_id = self.data_set.id
        conversation_id = conversation.id
        message = "Hello, this is my first message"
        streaming = False

        # Mock the get_answer method to create a response message
        mock_get_answer.return_value = None

        # When
        self.manager.respond_to_user_message(
            conversation_id=conversation_id,
            data_set_id=data_set_id,
            user_id=user_id,
            message=message,
            streaming=streaming,
        )

        # Then
        conversation.refresh_from_db()
        assert conversation.summary == message
        mock_get_answer.assert_called_once_with(conversation, message, streaming)

    @patch("agent.conversation.manager.ConversationManager.get_answer")
    def test_respond_to_user_message_subsequent_message_does_not_change_summary(self, mock_get_answer):
        """Test that subsequent messages don't change the conversation summary."""
        # Given
        conversation = Conversation.objects.create(
            user=self.user,
            data_set=self.data_set,
            started_at=datetime.now(),
            summary="Original summary",
            agent=self.agent,
        )
        user_id = self.user.id
        data_set_id = self.data_set.id
        conversation_id = conversation.id
        message = "This is a subsequent message"
        streaming = True

        # Mock the get_answer method to create a response message
        mock_get_answer.return_value = None

        # When
        self.manager.respond_to_user_message(
            conversation_id=conversation_id,
            data_set_id=data_set_id,
            user_id=user_id,
            message=message,
            streaming=streaming,
        )

        # Then
        conversation.refresh_from_db()
        assert conversation.summary == "Original summary"
        mock_get_answer.assert_called_once_with(conversation, message, streaming)

    @patch("agent.conversation.manager.ConversationManager.get_answer")
    def test_respond_to_user_message_with_invalid_conversation(self, mock_get_answer):
        """Test responding to message with invalid conversation."""
        # Given
        user_id = self.user.id
        data_set_id = self.data_set.id
        invalid_conversation_id = 99999
        message = "Test message"
        streaming = False

        # When & Then
        with pytest.raises(ObjectDoesNotExist):
            self.manager.respond_to_user_message(
                conversation_id=invalid_conversation_id,
                data_set_id=data_set_id,
                user_id=user_id,
                message=message,
                streaming=streaming,
            )

        # Verify get_answer was not called
        mock_get_answer.assert_not_called()

    @patch.object(IntegrationPluginResolver, "has_any", return_value=False)
    @patch.object(AgentRegistry, "get_agent_class_by_type")
    @patch.object(AgentRegistry, "get_conversation_agent")
    @patch.object(AgentRegistry, "aget_conversation_agent")
    def test_get_answer_uses_sync_path_when_data_set_has_no_tool_providing_integration(
        self, mock_aget_conversation_agent, mock_get_conversation_agent, mock_get_agent_class_by_type, mock_has_any
    ):
        """With nothing connected to fetch tools from, get_answer never touches the async path."""
        conversation = Conversation.objects.create(
            user=self.user, data_set=self.data_set, started_at=datetime.now(), agent=self.agent
        )
        mock_get_agent_class_by_type.return_value = type("AsyncCapableAgent", (), {"aget_answer": lambda self: None})
        mock_agent_instance = MagicMock()
        mock_agent_instance.get_answer.return_value = "sync answer"
        mock_get_conversation_agent.return_value = mock_agent_instance

        response = self.manager.get_answer(conversation, "hello", streaming=False)

        assert response == "sync answer"
        mock_get_conversation_agent.assert_called_once()
        mock_aget_conversation_agent.assert_not_called()

    @patch.object(IntegrationPluginResolver, "has_any", return_value=True)
    @patch.object(AgentRegistry, "get_agent_class_by_type")
    @patch.object(AgentRegistry, "get_conversation_agent")
    @patch.object(AgentRegistry, "aget_conversation_agent")
    def test_get_answer_uses_sync_path_when_agent_cannot_answer_asynchronously(
        self, mock_aget_conversation_agent, mock_get_conversation_agent, mock_get_agent_class_by_type, mock_has_any
    ):
        """An agent that only implements get_answer stays on the sync path, tools connected or not."""
        conversation = Conversation.objects.create(
            user=self.user, data_set=self.data_set, started_at=datetime.now(), agent=self.agent
        )
        mock_get_agent_class_by_type.return_value = type("SyncOnlyAgent", (), {})
        mock_agent_instance = MagicMock()
        mock_agent_instance.get_answer.return_value = "sync answer"
        mock_get_conversation_agent.return_value = mock_agent_instance

        response = self.manager.get_answer(conversation, "hello", streaming=False)

        assert response == "sync answer"
        mock_get_conversation_agent.assert_called_once()
        mock_aget_conversation_agent.assert_not_called()

    @patch.object(IntegrationPluginResolver, "has_any", return_value=True)
    @patch.object(AgentRegistry, "get_agent_class_by_type")
    @patch.object(AgentRegistry, "get_conversation_agent")
    @patch.object(AgentRegistry, "aget_conversation_agent", new_callable=AsyncMock)
    def test_get_answer_uses_async_path_when_tools_are_connected_and_agent_supports_it(
        self, mock_aget_conversation_agent, mock_get_conversation_agent, mock_get_agent_class_by_type, mock_has_any
    ):
        """A tool-providing integration on the data set moves an async-capable agent onto the async path."""
        conversation = Conversation.objects.create(
            user=self.user, data_set=self.data_set, started_at=datetime.now(), agent=self.agent
        )
        mock_get_agent_class_by_type.return_value = type("AsyncCapableAgent", (), {"aget_answer": lambda self: None})
        mock_agent_instance = MagicMock()
        mock_agent_instance.aget_answer = AsyncMock(return_value="async answer")
        mock_aget_conversation_agent.return_value = mock_agent_instance

        response = self.manager.get_answer(conversation, "hello", streaming=False)

        assert response == "async answer"
        mock_aget_conversation_agent.assert_awaited_once()
        mock_get_conversation_agent.assert_not_called()

    def test_record_error_creates_system_message(self):
        """Test that record_error creates a system error message."""
        # Given
        conversation = Conversation.objects.create(
            user=self.user,
            data_set=self.data_set,
            started_at=datetime.now(),
            agent=self.agent,
        )
        user_message = Message.objects.create(
            conversation=conversation, type=Message.MessageType.HUMAN, text="User's message"
        )
        user_id = self.user.id
        data_set_id = self.data_set.id
        conversation_id = conversation.id
        error = Exception("Test error message")

        # When
        self.manager.record_error(
            conversation_id=conversation_id, user_id=user_id, data_set_id=data_set_id, error=error
        )

        # Then
        user_message.refresh_from_db()
        assert conversation.messages.count() == 2
        error_message = conversation.messages.last()
        assert error_message.type == Message.MessageType.SYSTEM
        assert error_message.text == "We couldn't process your request at this time"
        assert error_message.created_at is not None
        assert user_message.answer_failed is True

    def test_record_error_with_invalid_conversation(self):
        """Test record_error with invalid conversation."""
        # Given
        user_id = self.user.id
        data_set_id = self.data_set.id
        invalid_conversation_id = 99999
        error = Exception("Test error message")

        # When & Then
        with pytest.raises(ObjectDoesNotExist):
            self.manager.record_error(
                conversation_id=invalid_conversation_id, user_id=user_id, data_set_id=data_set_id, error=error
            )

    def test_record_error_with_invalid_user(self):
        """Test record_error with invalid user."""
        # Given
        conversation = Conversation.objects.create(
            user=self.user,
            data_set=self.data_set,
            started_at=datetime.now(),
            agent=self.agent,
        )
        invalid_user_id = 99999
        data_set_id = self.data_set.id
        conversation_id = conversation.id
        error = Exception("Test error message")

        # When & Then
        with pytest.raises(ObjectDoesNotExist):
            self.manager.record_error(
                conversation_id=conversation_id, user_id=invalid_user_id, data_set_id=data_set_id, error=error
            )

    def test_record_error_with_invalid_data_set(self):
        """Test record_error with invalid data set."""
        # Given
        conversation = Conversation.objects.create(
            user=self.user,
            data_set=self.data_set,
            started_at=datetime.now(),
            agent=self.agent,
        )
        user_id = self.user.id
        invalid_data_set_id = 99999
        conversation_id = conversation.id
        error = Exception("Test error message")

        # When & Then
        with pytest.raises(ObjectDoesNotExist):
            self.manager.record_error(
                conversation_id=conversation_id, user_id=user_id, data_set_id=invalid_data_set_id, error=error
            )

    def test_record_error_with_different_error_types(self):
        """Test record_error with different types of exceptions."""
        # Given
        conversation = Conversation.objects.create(
            user=self.user,
            data_set=self.data_set,
            started_at=datetime.now(),
            agent=self.agent,
        )
        Message.objects.create(conversation=conversation, type=Message.MessageType.HUMAN, text="User's message")
        user_id = self.user.id
        data_set_id = self.data_set.id
        conversation_id = conversation.id

        # Test with different error types
        error_types = [
            ValueError("Value error"),
            RuntimeError("Runtime error"),
            KeyError("Key error"),
            TypeError("Type error"),
        ]

        # When & Then
        for error in error_types:
            self.manager.record_error(
                conversation_id=conversation_id, user_id=user_id, data_set_id=data_set_id, error=error
            )

            # Verify error message was created
            latest_message = conversation.messages.order_by("-created_at").first()
            assert latest_message.type == Message.MessageType.SYSTEM
            assert latest_message.text == "We couldn't process your request at this time"
