import mimetypes
from abc import ABC, abstractmethod
from typing import IO, AnyStr


class FileServiceException(Exception):
    """Base error for file processing."""


class NotSupportedFileTypeException(FileServiceException):
    """Raised when a file's type is not supported."""

    def __init__(self, message: str = "Unsupported file type.") -> None:
        super().__init__(message)


class FileParsingException(FileServiceException):
    """Raised when a file's content cannot be extracted."""

    def __init__(self, message: str = "Failed to extract content from file.") -> None:
        super().__init__(message)


class BaseFileParser(ABC):
    """Extracts text from one type of file."""

    @abstractmethod
    def parse_content(self, file: IO[AnyStr]) -> str:
        """Return the file's text content."""


class BaseFileService(ABC):
    """Processes an uploaded file."""

    def __init__(self, file: IO[AnyStr], content_type: str):
        self.file = file
        self.content_type = content_type

    @abstractmethod
    def process(self) -> str:
        """Return the file's text content."""

    @abstractmethod
    def _get_parser(self) -> BaseFileParser:
        pass

    def _get_file_type(self) -> str:
        return mimetypes.guess_extension(self.content_type)
