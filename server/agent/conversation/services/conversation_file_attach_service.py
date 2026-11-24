import os

from django.core.files.base import ContentFile

from agent.conversation.services.conversation_file_message_service import ConversationFileMessageService
from agent.conversation.services.file_parsing_service import FileParsingService
from agent.models.agent import Agent
from agent.models.conversation import Conversation, ConversationFile
from pecl import settings


class UnsupportedFileTypeError(Exception):
    def __init__(self, ext: str, supported: list[str]):
        self.ext = ext
        self.supported = supported
        super().__init__(f"File type '{ext}' is not supported. Supported: {', '.join(supported)}.")


class FileUploadNotSupportedError(Exception):
    pass


class ConversationFileAttachService:
    def validate(self, agent: Agent, filenames: list[str]) -> None:
        if not filenames:
            return
        if not agent.file_upload:
            raise FileUploadNotSupportedError()

        supported = [ext for extensions in settings.FILE_PARSER_CLASSES for ext in extensions]
        for filename in filenames:
            ext = os.path.splitext(filename)[1].lower()
            if ext not in supported:
                raise UnsupportedFileTypeError(ext, supported)

    def attach(self, conversation: Conversation, name: str, content: bytes, content_type: str) -> ConversationFile:
        file_category = (
            ConversationFile.FileCategory.IMAGE
            if content_type.startswith("image/")
            else ConversationFile.FileCategory.FILE
        )
        django_file = ContentFile(content, name=name)
        conversation_file = ConversationFile.objects.create(
            conversation=conversation,
            file=django_file,
            file_category=file_category,
            content_type=content_type,
            llm_content=FileParsingService(django_file, content_type).process() or "",
            is_hidden=False,
        )
        ConversationFileMessageService.create_for_file(conversation_file)
        return conversation_file
