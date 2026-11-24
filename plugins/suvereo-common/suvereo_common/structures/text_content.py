from suvereo_common.structures.base_content import BaseContent


class TextContent(BaseContent):
    """Text passed to a language model."""

    text: str
