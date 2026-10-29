import json
from collections.abc import Iterator


class JsonReply:
    """Reads a model's text reply for the JSON objects in it, such as a verdict wrapped in prose."""

    @staticmethod
    def objects(reply: str) -> Iterator[dict]:
        """Every JSON object in the reply, in order; text around and between them is skipped."""
        decoder = json.JSONDecoder()
        for start in (i for i, char in enumerate(reply) if char == "{"):
            try:
                value, _ = decoder.raw_decode(reply, start)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                yield value
