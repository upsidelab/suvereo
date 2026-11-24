from dataclasses import dataclass
from typing import Any

from suvereo_common.structures.file_types import FileTypes


@dataclass
class LLMFile:
    """A conversation file prepared for a language model."""

    id: Any
    content: str
    file_category: FileTypes
    filename: str
    content_type: str
