# ADR-0005: JWT access and refresh tokens for users

## Status

Accepted

## Context

Authentication was based on never-expiring API keys, held by both users and service accounts.

Service accounts handled their keys explicitly: the key was shown once, when the service account was created, and was used for programmatic API access.

Users authenticated with a password, but login returned the same kind of API key, and the frontend persisted it in the browser's local storage. If such a key leaked (for example through an XSS attack), the attacker would have indefinite access to the user's identity.

## Decision

Users authenticate with short-lived JWT access tokens and refresh tokens. The API key mechanism is retired for users and kept for service accounts.

- **Login returns an access and a refresh token.** The access token is short-lived (15 minutes by default) and the refresh token expires after 7 days by default. Both lifetimes are configurable.
- **Refresh tokens are rotated.** Refreshing returns a new token pair and revokes the old refresh token, so an already-used refresh token is rejected. Changing a user's password revokes their outstanding refresh tokens.
- **The library is `djangorestframework-simplejwt`, and JWT is a consequence of that choice.** It provides most of what was needed out of the box: login, logout and refresh views, access and refresh token logic, and a token blacklist for invalidation. Reusing a well-tested, established library was preferred over building these features from scratch. The revocation of a user's refresh tokens on password change is our own service, built on the library's blacklist.
- **Tokens are sent in the `Authorization` header** with the `Bearer` prefix. Cookies were considered and not implemented. The frontend and the API are separate, so the frontend can be hosted on a different site, which rules out SameSite cookies, and the API can be used without the frontend. The frontend keeps the refresh token in local storage and the access token only in memory, and a page reload triggers a refresh to obtain a new access token.
- **Service accounts keep API keys**, sent with the `Token` prefix, unchanged for backwards compatibility. The server supports two `Authorization` prefixes, one per authentication method. `Bearer` was chosen for JWT because it is the standard prefix for it, and `Token` did not fit semantically.
- **Users are no longer issued an API key at all.** Previously one was created at first login.
- **WebSocket connections authenticate with tickets.** A ticket is single-use, tied to one user and short-lived (10 seconds by default), and is passed in the connection's query string.
- **Django sessions are not used.** The session machinery was removed.

## Consequences

- A leaked access token is useful for minutes rather than indefinitely. A leaked refresh token is limited by its expiry and by rotation.
- Because the refresh token stays in local storage, an XSS attack can still steal it. The exposure is reduced, not eliminated.
- Clients must handle token expiry and refresh. Programmatic clients that don't want to should use a service account.
- Programmatic API access is a service account concern. A user's credentials are not meant for scripts, and there is no API key for users to create.
- Authentication behavior follows the library, and the choice of JWT is tied to it. Replacing the library would mean replacing the token format and the revocation mechanism too.
- Anything that authenticates a request has to account for two schemes, `Bearer` and `Token`. WebSockets are a third path, through tickets.
