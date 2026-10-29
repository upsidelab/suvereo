"""Making requests to a third party without letting a form value reach our own network."""

import ipaddress
import socket
from typing import Any
from urllib.parse import urlparse

import httpx

from .errors import OAuthError

# Required: Notion, Asana, Atlassian, Sentry and PayPal all sit behind a WAF that answers
# 403 to non-browser clients, so discovery fails before any OAuth question is asked.
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
)

# Kept short because a lapsed token is renewed inline while an agent is answering.
TIMEOUT = 5.0

MAX_REDIRECTS = 5


def require_public_url(url: str) -> str:
    """Reject anything that would make the server fetch from its own network."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise OAuthError("Enter an http:// or https:// URL.")
    if not parsed.hostname:
        raise OAuthError("That URL has no host.")

    try:
        resolved = socket.getaddrinfo(parsed.hostname, None)
    except socket.gaierror as e:
        raise OAuthError(f"Could not resolve {parsed.hostname}.") from e

    for *_, address in resolved:
        ip = ipaddress.ip_address(address[0])
        if not ip.is_global:
            raise OAuthError(
                f"{parsed.hostname} resolves to a private address. Connect only works with servers "
                "reachable on the public internet."
            )
    return url


def open_client() -> httpx.Client:
    return httpx.Client(timeout=TIMEOUT, follow_redirects=False, headers={"User-Agent": USER_AGENT})


def send(client: httpx.Client, method: str, url: str, **kwargs: Any) -> httpx.Response:
    """Make a request, following redirects one vetted hop at a time."""
    for _ in range(MAX_REDIRECTS):
        response = client.request(method, require_public_url(url), **kwargs)
        if not response.is_redirect or not (location := response.headers.get("Location")):
            return response
        url = str(response.next_request.url) if response.next_request else location
        if response.status_code not in (307, 308):
            method, kwargs = "GET", {k: v for k, v in kwargs.items() if k == "headers"}
    raise OAuthError("That server redirected too many times.")


def request(method: str, url: str, **kwargs: Any) -> httpx.Response:
    """Make one vetted request to a third party, following redirects a hop at a time."""
    with open_client() as client:
        return send(client, method, url, **kwargs)


def get_json(client: httpx.Client, url: str) -> dict[str, Any]:
    response = send(client, "GET", url, headers={"Accept": "application/json"})
    response.raise_for_status()
    return response.json()
