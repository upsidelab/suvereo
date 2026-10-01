# JWT Authentication

## Summary

Up to commit `8b35f8d`, frontend auth relied on a never-expiring API key kept in `localStorage`. This spec replaced it with **short-lived access tokens + rotating refresh tokens** issued by `djangorestframework-simplejwt`, while keeping **API keys unchanged for service accounts**.

**Status:** implemented. All phases below are applied; file and line references in the Implementation section describe the code as it was at `8b35f8d`.

**Requirements:**
- Service-account API keys keep working as they do today
- The frontend and backend may be deployed separately (different origins)
- Other backends (e.g. an ecommerce store) can use the API on behalf of their users
- Anonymous sessions (guests using agents) can be added later without changing the auth model

**Why no cookies:** with separate deploys, cookies become cross-site. They then need `SameSite=None` and CSRF handling, and browsers such as Safari block them outright. Tokens sent in headers work the same way for any frontend and any origin, and never need CSRF protection.

---

## Design

### 1. Service accounts: unchanged
DRF `TokenAuthentication` with the `Authorization: Token <key>` header stays, listed next to simplejwt's `JWTAuthentication` in `DEFAULT_AUTHENTICATION_CLASSES`. Hashing keys at rest can be done as a separate change.

### 2. Human login
`TokenObtainPairView` returns both tokens in the response body:
- **Access token**: a short-lived JWT (see Lifetimes). The frontend keeps it in memory only and sends it as `Authorization: Bearer <token>`. `JWTAuthentication` loads the user on every request, so deactivating a user takes effect immediately.
- **Refresh token**: a longer-lived JWT, rotated on every use. The frontend keeps it in `localStorage` so the login survives page reloads.

### 3. Refresh / logout
Built on simplejwt with the `token_blacklist` app, which records every issued refresh token (`OutstandingToken`) and every revoked one (`BlacklistedToken`).

- `refresh` (`TokenRefreshView`): takes the refresh token in the JSON body and returns a new pair. With `ROTATE_REFRESH_TOKENS` + `BLACKLIST_AFTER_ROTATION`, the previous refresh token is rejected from then on.
- `logout` (`TokenBlacklistView`): blacklists the refresh token. The access token stays valid until it expires.
- A password change blacklists all of the user's outstanding refresh tokens, and `CHECK_REVOKE_TOKEN` rejects access tokens issued before the change.
- **Tabs refreshing at once**: tabs share the refresh token through `localStorage`. `ApiClient` wraps refresh in `navigator.locks.request('auth-refresh', …)` and re-reads the token from `localStorage` inside the lock. A tab waiting on the lock then uses the already-rotated token instead of sending a blacklisted one.
- When refresh fails (expiry, blacklisting), the frontend redirects to login with a "session expired" message and takes the user back to the page they were on after login.
- `flushexpiredtokens` (scheduled with Celery beat) removes expired rows from the blacklist tables.

### Lifetimes
Configured in `SIMPLE_JWT` settings, overridable from env. All values are whole seconds:

```
ECL_AUTH_ACCESS_TOKEN_TTL_SECONDS     = 900       # ACCESS_TOKEN_LIFETIME (15 minutes)
ECL_AUTH_REFRESH_TOKEN_TTL_SECONDS    = 604800    # REFRESH_TOKEN_LIFETIME (7 days)
ECL_AUTH_WS_TICKET_TTL_SECONDS        = 10        # WS_TICKET_TTL_SECONDS (WebSocket ticket, see §5)
```

The refresh window is **sliding**: each rotation issues a refresh token with a fresh 7-day lifetime (simplejwt's default). Active users stay logged in; users idle for more than 7 days log in again. The access token lifetime is also the longest an access token stays usable after logout or revocation, so it should stay short.

### 4. Security
- Injected script (XSS) can read a refresh token kept in `localStorage`. The damage is limited by rotation: once the victim or the attacker refreshes, the other side's copy of the token is rejected.
- A Content Security Policy on the frontend (`script-src 'self'`, no inline scripts) blocks most injected scripts.
- The sanitizing of rendered agent output (markdown via `marked` + `DOMPurify`) must be kept on every rendering path. Agent output can be steered by prompt injection in synced product data and documents.
- Tokens are signed with a dedicated `SIGNING_KEY` from env, separate from `SECRET_KEY`, so each key can be rotated on its own.
- The browser never attaches tokens to requests on its own, so the API can't be the target of CSRF attacks. CORS allows only the configured frontend origins.

### 5. WebSocket
Browsers can't set headers on a WebSocket handshake, so the client first fetches a single-use ticket (an ordinary authenticated `POST`) that expires within seconds and passes it in the connect URL. A custom Channels middleware redeems the ticket and loads the user, so authentication stays in middleware and no token ever appears in a URL. The connection is also checked for origin and for conversation-level access.

### 6. Token exchange for backend clients (future)
A backend acting for its users (e.g. an ecommerce store) authenticates with its service-account key and gets tokens for a given user from a dedicated endpoint (`RefreshToken.for_user(user)`).

### 7. Anonymous sessions (future)
A guest endpoint issues tokens with no user and custom claims limiting their scope (specific agents only, rate-limited, short-lived). They're validated by a custom authentication class built on simplejwt's stateless token authentication.

---

## Rollout

1. Add simplejwt and the token endpoints alongside the current auth. No behaviour change yet.
2. Move the frontend to the new tokens (access token in memory, refresh token in `localStorage`, refresh done silently in `ApiClient`) and stop storing the API key.
3. Secure the WebSocket connection (replaces `AuthMiddlewareStack`).
4. Retire Django sessions, which nothing uses since the Django admin was removed: remove `django.contrib.sessions`, `django.contrib.messages` and their middleware, plus `AuthenticationMiddleware`. Remove `CsrfViewMiddleware` once it's confirmed that no non-DRF view relies on it. The orphaned `django_session` table can be dropped with a migration.

---

## Implementation

Each phase is one PR-sized, independently shippable commit (or small stack of commits). Phases follow the Rollout order; phase 2 is split because the `ApiClient` change is the largest.

### Phase 1 — Backend: simplejwt alongside API keys (no behaviour change)

**Dependencies** — `server/pyproject.toml`: add `djangorestframework-simplejwt` (pinned, like the other deps; ≥5.3 for `CHECK_REVOKE_TOKEN`). `poetry lock`.

**Settings** — `server/pecl/settings.py`:
- `INSTALLED_APPS`: add `rest_framework_simplejwt` and `rest_framework_simplejwt.token_blacklist`.
- `REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"]`: `JWTAuthentication` first, `TokenAuthentication` second. Both use `Authorization`, but different keywords (`Bearer` / `Token`), so each class ignores the other's header.
- New `SIMPLE_JWT` block:
  - `ACCESS_TOKEN_LIFETIME` / `REFRESH_TOKEN_LIFETIME` from `ECL_AUTH_ACCESS_TOKEN_TTL_SECONDS` / `ECL_AUTH_REFRESH_TOKEN_TTL_SECONDS` (default 900 / 604800, i.e. 15 minutes / 7 days). Env values are integers in seconds, read with `env.int()` and wrapped in `timedelta(seconds=…)`.
  - `SIGNING_KEY` from a new required `ECL_AUTH_SIGNING_KEY` (fail at startup like `ECL_DJANGO_SECRET_KEY` at line 25).
  - `ROTATE_REFRESH_TOKENS`, `BLACKLIST_AFTER_ROTATION`, `CHECK_REVOKE_TOKEN` = `True`; `UPDATE_LAST_LOGIN = True`.
  - `User.USERNAME_FIELD` is already `email`, so `TokenObtainPairSerializer` accepts `{ email, password }` without a subclass.
- `CELERY_BEAT_SCHEDULE`: add a daily `flush_expired_tokens` entry.
- `SWAGGER_SETTINGS["SECURITY_DEFINITIONS"]`: add a `Bearer` definition next to `Token`.
- Env files / `docker-compose*.yml` / `.env` samples: add `ECL_AUTH_SIGNING_KEY` and the two TTLs.

**Celery task** — `server/account/tasks.py` (new): `flush_expired_tokens` calling `call_command("flushexpiredtokens")`.

**Endpoints** — `server/account/urls.py`:
- `api/auth/token/refresh` → `TokenRefreshView`
- `api/auth/logout` → `TokenBlacklistView`

`api/auth/login` keeps its path and becomes the token-pair endpoint, but it changes in phase 2b together with the frontend, because swapping its response here would break the current login. Tests in this phase get their pair from `RefreshToken.for_user(user)`. The tests that log in through the endpoint move to 2b.

**Password change revokes sessions** — `server/account/serializers/users.py:74` (`UserUpdatePasswordSerializer.update`): after `set_password`, blacklist all of the user's `OutstandingToken`s. Implemented as `RefreshTokenRevocationService.revoke_all(user)` (`account/services/refresh_token_revocation.py`) so a future self-service password change reuses it. Access tokens are covered by `CHECK_REVOKE_TOKEN` (the claim is a hash of the password).

**Tests** — `server/account/tests/test_views/test_auth.py` (new):
- obtain returns a pair; wrong password / inactive user → 401
- a `Bearer` access token authenticates `api/account`; a `Token` key still does
- refresh rotates, the old refresh token is then rejected
- logout blacklists the refresh token
- password change: old refresh rejected, old access rejected
- deactivating a user rejects their still-valid access token

Also: `account/tests/test_views/test_accounts.py:14` `FRAMEWORK_PREFIXES` — add `token_blacklist.` so the blacklist app's permissions don't leak into that assertion.

### Phase 2a — Frontend: central authenticated fetch in the API client

Implemented together with 2b: the method is `BaseApiClient.authenticatedFetch()`, and `ApiClient` now extends `BaseApiClient`. `authenticatedFetch()` also applies the default JSON `Content-Type` (left unset for `FormData` bodies), so `_requestConfiguration()` is removed and callers pass only `method` / `body`.

- `frontend/src/lib/api/base.ts`: add `protected fetch(input, init)` (name e.g. `_authorizedFetch`) that merges `_requestConfiguration()` headers into `init` and calls `window.fetch`. Callers that need custom headers (FormData uploads in `conversations.ts:156` and `agentic-executions.ts:51` delete `Content-Type`) must keep working — let the method accept `init.headers` overrides, with a way to omit `Content-Type`.
- Replace all `fetch(url, { ...this._requestConfiguration(), … })` calls in `frontend/src/lib/api/*.ts` (~80 call sites) and `frontend/src/lib/api.ts` (`getAccount`, `getAllUsers`, `getAdmins`, …) with the new method. `ApiClient` itself doesn't extend `BaseApiClient` today — either make it extend it, or share the method via a small `AuthorizedFetcher` object that both use.
- Remove the duplicated `_requestConfiguration()` from `api.ts:161`.

### Phase 2b — Frontend: access + refresh tokens

**`frontend/src/lib/authentication-provider.ts`** — replace `DummyAuthenticationProvider` with a `TokenAuthenticationProvider`:
- `accessToken` held in memory only; `refreshToken` in `localStorage` (key e.g. `refreshToken`); on construction, delete the legacy `token` key.
- `isAuthenticated()` → a refresh token exists (the access token is lost on reload and fetched lazily).
- `login(access, refresh)`, `logout()` (clears both).
- `refreshAccessToken()`: runs inside `navigator.locks.request('auth-refresh', …)` and reads the refresh token from `localStorage` *inside* the lock, so a tab that waited sends the token the previous holder just rotated, never a blacklisted one. Concurrent calls within one tab share a single in-flight refresh. A `401` from the refresh endpoint signs out and throws `SessionExpiredError`; other failures (network, 5xx) throw without signing out.
- Listen to the `storage` event for the refresh key: removal in another tab ends the session here too. Session ends are reported through `onSessionEnded(reason)` (`expired` / `signedOutElsewhere`).

**`frontend/src/lib/api/base.ts`** (the method from 2a):
- Send `Authorization: Bearer <access>`. If there is no access token yet (page reload), refresh first.
- On `401`, refresh once and retry the request once — skipping the refresh when a concurrent request already replaced the token. If refresh fails, the `401` response is returned unchanged, so existing error handling (e.g. the root loader) keeps working.
- Callers pass `FormData` bodies, which can be re-sent; no streamed bodies, so retry is safe.

**Login endpoint (backend)** — `server/account/views/login.py`: replace the current `LoginView` with a subclass of `TokenObtainPairView` on the same `api/auth/login` route. It still accepts `{ email, password }` and now returns `{ access, refresh }` instead of `{ token }`. Human users stop getting API keys from here on. Update the swagger schema and the login tests. This backend change and the frontend change below ship in one commit.

**Login (frontend)** — `frontend/src/lib/api.ts:46` `login()`: keeps calling `api/auth/login`, returns `{ access, refresh }` (update the `Token` type usage — service accounts still use `Token`, so add a separate `TokenPair` type). `frontend/src/components/login/login-form.tsx:56`: pass both tokens; after login navigate to the `next` query param if present (validate it's a same-origin relative path), else `/`.

**Logout** — `frontend/src/components/navigation/user-menu.tsx:21`: call `POST api/auth/logout` with the refresh token (best effort, ignore failures), then clear tokens.

**Session expiry redirect** — `frontend/src/main.tsx`:
- `signOutAndReturnToLogin` (line 40): redirect to `/login?expired=1&next=<current path>`.
- Refresh failures outside loaders (inside components) need the same redirect: the auth provider exposes `onSessionEnded(reason)`, which `main.tsx` wires to `router.navigate(...)`.
- Login page (`frontend/src/pages/login.tsx` / `login-form.tsx`): show "Your session has expired, please log in again" when `expired=1`.

### Phase 2c — Frontend: Content Security Policy

- The frontend container serves the build with `vite preview` (`frontend/docker-entrypoint.sh`), so the header is set in `preview.headers` in `frontend/vite.config.ts`. The entrypoint builds at container start, so `connect-src` picks up the deploy's `VITE_API_BASE` / `VITE_WS_BASE`. `img-src` allows `https:` (agent answers embed product images from store hosts) plus the API origin (media), and `style-src` needs `'unsafe-inline'` for Radix.
- Verify no inline scripts in `frontend/index.html` (none today) and that Vite's build emits none. Dev server is left without CSP.
- Check `message-bubble.tsx:22` is the only place rendering agent HTML (`dangerouslySetInnerHTML`); grep for other uses and route them through the same `marked` + `DOMPurify` helper — extract it into `frontend/src/lib/render-markdown.ts` so every path uses it.

### Phase 3 — Secure the WebSocket

Decision: **ticket** rather than first-message auth, because it keeps authentication in middleware (the connection is rejected before `connect()` runs) and the token never appears in a URL.

- **Ticket endpoint** — `api/auth/ws_ticket` (`server/account/views/ws_ticket.py`, logic in `account/services/ws_tickets.py` `WebSocketTicketService`): authenticated `POST` returns a random ticket stored in the Django cache as `ws_ticket:<ticket> → user_id` for `WS_TICKET_TTL_SECONDS` (`ECL_AUTH_WS_TICKET_TTL_SECONDS`, default 10). Adds a `CACHES` entry (none existed) — a Redis cache reusing the existing Redis.
- **Middleware** — `server/agent/ws_auth.py` (new) `TicketAuthMiddleware`: reads `ticket` from the query string, redeems it from the cache (single use: `cache.delete()` returns `True` only for the caller that removed the key, so parallel redeems can't both succeed), loads the user (reject inactive), sets `scope["user"]`, else `AnonymousUser`.
- **`server/pecl/asgi.py`**: replace `AuthMiddlewareStack` with `OriginValidator(TicketAuthMiddleware(URLRouter(...)), CORS_ALLOWED_ORIGINS)` — not `AllowedHostsOriginValidator`, since frontend and API may be on different hosts. The frontend origin must be listed in `ECL_DJANGO_CORS_ALLOWED_ORIGINS`, or every WebSocket connection is rejected (the chat then falls back to polling).
- **`server/agent/consumers.py:7` `ChatConsumer.connect`**: close (code `4401`) if the user is anonymous; close (`4403`) if the conversation isn't visible to them — reuse the same filter as `ConversationView.get` (`agent/views.py:74`: owner or `CONVERSATION.VIEW_ALL` on the data set). Extracted into `Conversation.objects.visible_to(user)`, used by the consumer (wrapped in `database_sync_to_async`), `ConversationView` and the conversation list. Note: closing before `accept()` makes the server reject the handshake with a plain HTTP 403, so browsers never see `4401` / `4403` — only the tests do. The frontend doesn't distinguish failures today (it always falls back to polling); accepting first and then closing would expose the codes.
- **Frontend** — `frontend/src/components/conversation-view/chat-session.tsx:216`: fetch a ticket via a new `api.conversations().getWebSocketTicket()` (goes through the refreshing fetch), then open `…/ws/chat/<id>/?ticket=<t>`. Reconnects fetch a new ticket. Existing fallback to polling on failure stays.
- **Tests** — `server/agent/tests/test_consumers.py` with Channels' `WebsocketCommunicator`: no ticket, expired/reused ticket, other user's conversation, wrong origin → rejected; valid → accepted. Ticket view tests.

### Phase 4 — Retire Django sessions

- `pecl/settings.py`: remove `django.contrib.sessions`, `django.contrib.messages` from `INSTALLED_APPS`; remove `SessionMiddleware`, `AuthenticationMiddleware`, `MessageMiddleware`; remove the `messages` context processor from `TEMPLATES`. `django.contrib.auth.context_processors.auth` depends on `AuthenticationMiddleware` — remove it too.
- `CsrfViewMiddleware`: removed. Every route is a DRF view (drf-yasg's `get_schema_view` included), and DRF views are CSRF-exempt without `SessionAuthentication`.
- `SWAGGER_SETTINGS["USE_SESSION_AUTH"]` is already `False`.
- Migration `account/migrations/0014_drop_django_sessions.py`: `RunSQL("DROP TABLE IF EXISTS django_session")` (the sessions app's own migrations go away with the app), and it deletes the `sessions` content type so its stale permission rows don't linger in `get_all_permissions()`. Neither step is reversible: rolling back does not recreate the table.
- `account/tests/test_views/test_accounts.py:14`: drop `sessions.` from `FRAMEWORK_PREFIXES`.
- Run the full test suite and the swagger page manually.

### Out of scope here
Hashing service-account keys at rest, token exchange for backend clients (Design §6), anonymous sessions (Design §7).
