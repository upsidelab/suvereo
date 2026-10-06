from unittest.mock import patch

import pytest
from model_bakery import baker

from agent.conversation.services import (
    ConversationFileAttachService,
    FileUploadNotSupportedError,
    UnsupportedFileTypeError,
)
from agent.models.agent import Agent
from agent.models.conversation import Conversation, ConversationFile

pytestmark = pytest.mark.django_db

SERVICE = "agent.conversation.services.conversation_file_attach_service"


@pytest.fixture(autouse=True)
def _parsers():
    with (
        patch(f"{SERVICE}.settings.FILE_PARSER_CLASSES", {(".pdf", ".png"): "some.parser.Class"}),
        patch(f"{SERVICE}.FileParsingService.process", return_value="parsed"),
    ):
        yield


class TestConversationFileAttachService:
    def test_validate_accepts_no_files_even_when_uploads_are_off(self):
        ConversationFileAttachService().validate(baker.make(Agent, file_upload=False), [])

    def test_validate_rejects_files_when_uploads_are_off(self):
        with pytest.raises(FileUploadNotSupportedError):
            ConversationFileAttachService().validate(baker.make(Agent, file_upload=False), ["a.pdf"])

    def test_validate_rejects_an_unparseable_extension(self):
        with pytest.raises(UnsupportedFileTypeError):
            ConversationFileAttachService().validate(baker.make(Agent, file_upload=True), ["a.pdf", "b.xyz"])

    def test_attach_stores_raw_bytes_with_their_parsed_content(self, temp_media_root):
        conversation = baker.make(Conversation)

        stored = ConversationFileAttachService().attach(conversation, "order.png", b"bytes", "image/png")

        assert stored.conversation == conversation
        assert stored.file_category == ConversationFile.FileCategory.IMAGE
        assert stored.llm_content == "parsed"
        assert conversation.messages.count() == 1
