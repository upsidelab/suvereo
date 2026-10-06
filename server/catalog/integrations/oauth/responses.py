"""What the popup is sent once the exchange is done, or once it cannot be."""

from urllib.parse import quote

from django.http import HttpResponse, HttpResponseRedirect
from django.utils.html import escape

#: Path on the frontend the popup is handed back to once the exchange is done.
COMPLETE_PATH = "/oauth/complete"


def hand_back(state: str, origin: str) -> HttpResponse:
    """Return the popup to the frontend, which can then tell the form without any polling."""
    if not origin:
        return message_page("Could not return to the app. Close this window and try again.")
    return HttpResponseRedirect(f"{origin}{COMPLETE_PATH}?state={quote(state)}")


def message_page(text: str) -> HttpResponse:
    """Shown only when the popup cannot be sent back to the app it came from."""
    return HttpResponse(
        f"""<!doctype html>
<meta charset="utf-8">
<title>Connecting…</title>
<body style="font:14px system-ui;padding:2rem;color:#444"><p>{escape(text)}</p></body>"""
    )
