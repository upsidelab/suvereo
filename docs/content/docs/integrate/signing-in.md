# Signing In and Token Refresh

This page is for clients that call the API on behalf of a person, such as a custom front end. Scripts and other systems should use a [service account](/docs/integrate/manage-api-keys) instead, whose `Token` header does not expire and does not need refreshing, see [Connecting to the API](/docs/integrate/connect-to-api).

A user signs in with their email and password and receives two JWT tokens:

- an **access token**, which is sent with requests. It is short-lived: 15 minutes by default.
- a **refresh token**, which is exchanged for a new pair of tokens. It expires after 7 days by default.

The lifetimes are instance settings, `ECL_AUTH_ACCESS_TOKEN_TTL_SECONDS` and `ECL_AUTH_REFRESH_TOKEN_TTL_SECONDS`.

User tokens are sent with the `Bearer` prefix, which is different from the `Token` prefix of service accounts:

```
Authorization: Bearer <ACCESS_TOKEN>
```

## Sign In

```http
POST /api/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "<password>"
}
```

**Response:**
```json
{
  "access": "<access token>",
  "refresh": "<refresh token>"
}
```

Returns 401 for invalid credentials.

## Refresh the Tokens

When the access token expires, requests are rejected with 401. Exchange the refresh token for a new pair:

```http
POST /api/auth/token/refresh
Content-Type: application/json

{
  "refresh": "<refresh token>"
}
```

The response has the same shape as the sign-in response. Refresh tokens are rotated: the one you sent is revoked, so only the new one can be used next. Returns 401 if the refresh token is invalid, expired or already used. Changing a user's password also revokes their refresh tokens, so the person has to sign in again.

## Sign Out

```http
POST /api/auth/logout
Content-Type: application/json

{
  "refresh": "<refresh token>"
}
```

The refresh token is revoked. The access token remains valid until it expires.

## WebSocket Connections

[Conversations](/docs/concepts#conversation) stream answers over a WebSocket. A WebSocket connection is authenticated with a ticket. Request one with an authenticated request, and pass it in the `ticket` query parameter when opening the connection:

```http
POST /api/auth/ws_ticket
Authorization: Bearer <ACCESS_TOKEN>
```

**Response (`201 Created`):**
```json
{
  "ticket": "<ticket>"
}
```

A ticket can be used once and expires after 10 seconds by default.
