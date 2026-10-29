# ADR-0006: MCP servers as tool-providing integrations, connected with OAuth

## Status

Accepted

## Context

Agents could only call the tools their plugin declared in code. Many external systems (Notion, Asana, Atlassian, in-house services) expose their actions through an MCP (Model Context Protocol) server, and connecting one to an agent took a code change and a deploy.

Integrations existed only as data sources (products, documents, e-commerce), capped at one per type per data set. Credentials were config fields the admin had to fill in by hand, which for an MCP server meant finding and pasting a long-lived token.

## Decision

MCP support is an optional plugin, `suvereo-integration-mcp`, built on two generic capabilities added to `suvereo-common`: integrations that provide tools, and integrations that authorize with OAuth. The server handles those two interfaces only.

- **Integrations can provide tools.** `BaseToolProvidingIntegration.get_tools()` returns LangChain tools. When the agent is built for a conversation turn, `AgentBuilder` resolves every tool-providing integration on the data set (`resolve_all`) and adds their tools to the agent's own. Tools are enabled per data set: every agent on that data set that can answer asynchronously receives them.
- **One integration instance is one MCP server.** `ALLOWS_MULTIPLE_INSTANCES` lets a data set hold several, each told apart by `instance_name()` (the admin-given name, or the host). Each server gets its own client. A server that fails or takes longer than 10 seconds loses only its own tools for that turn; the failure is logged and the other servers' tools are kept.
- **The async path is taken only when needed.** MCP clients are async. `ConversationManager` answers through `aget_answer` only when the agent implements it and the data set has a tool-providing integration. The check (`has_any`) reads the stored integration records only, so it is cheap on every turn. Every other conversation keeps the sync path. Today `BaseToolCallingAgent` is the only agent with `aget_answer`.
- **Transports are streamable HTTP (default) and SSE.** Every MCP server is reached over the network.
- **Credentials are two flat fields, `auth_header` and `auth_token`.** The admin form renders one input per config field, so a credential is stored as one header name and one value. This covers bearer and API-key servers. An admin can paste a token, or press Connect to fill both fields through OAuth.
- **OAuth is a generic capability in `suvereo-common`.** `BaseOAuthIntegration` declares `oauth_start`, `oauth_exchange_code` and `oauth_refresh`. The protocol lives in `suvereo_common.oauth`: discovery from a `WWW-Authenticate` challenge, dynamic client registration, PKCE (S256), the `resource` parameter, code exchange and refresh. The MCP plugin adds only the probe that provokes the challenge (`suvereo_integration_mcp.oauth.discover`). The server's views in `catalog/integrations/oauth/` serve any subclass, detected with `issubclass`. The first version kept OAuth inside the MCP plugin. Review of PR #47 moved it to `suvereo-common`, so the server's OAuth endpoints depend on a shared interface and serve any integration type that implements it.
- **The handshake runs in a popup, and the credential returns through the server.**
  1. Start stores the pending flow in the cache under its `state` for 15 minutes.
  2. The provider redirects to an unauthenticated callback, which exchanges the code and stores the result for 5 minutes.
  3. The callback redirects the popup to the frontend's `/oauth/complete`, which notifies the form over a `BroadcastChannel`.
  4. The form collects the result. The server checks that the user is the one who started the flow, and that they still hold the permission.

  The credential travels only in the API response to that authenticated request. The popup returns only to an origin listed in `CORS_ALLOWED_ORIGINS`. The callback base URL is configurable with `ECL_OAUTH_BASE_URL`.
- **Public-client registrations are reused.** A registration with no client secret is cached for 30 days per integration type, server and redirect URI, so pressing Connect again reuses it. A registration the provider rejects is forgotten. Confidential clients, which come with a secret, register again on each Connect.
- **Tokens renew themselves.**
  - Before fetching tools, the plugin renews an access token that is within 60 seconds of expiry. It writes the new token back through a config writer the server injects with `set_config_writer`.
  - A failed renewal waits 60 seconds before the next try.
  - After 10 consecutive failures, the integration reports `needs_reconnect`, and the UI asks for a fresh Connect.
  - An admin can also renew on demand (`IntegrationOAuthRefreshView`).
- **Outbound OAuth requests are restricted.**
  - Every URL, including each redirect hop (at most 5), must resolve to a public address.
  - Requests time out after 5 seconds.
  - A browser `User-Agent` is sent, because several providers' firewalls reject other clients.
- **Permissions:** connecting needs `INTEGRATION.ADD` or `INTEGRATION.CHANGE` on the data set, and renewing on demand needs `INTEGRATION.CHANGE`.

## Consequences

- A data set admin can give agents new tools by configuring an integration. Any integration type can provide tools or use OAuth by implementing the same interfaces.
- An MCP server is trusted like code. Its tool descriptions and results go into the agent's prompt, so a malicious or compromised server can steer the agent. Who may connect servers is controlled by the integration permissions alone.
- Tokens, refresh tokens included, are stored in plain text in `Integration.config`. The integrations API returns them to anyone who can view integrations; the form only hides them. Encrypting or redacting them is open work.
- The public-address check covers the OAuth requests only. The MCP connection itself goes to whatever URL is configured, so an admin can point a server at an internal address with a pasted token. Servers on private networks need a pasted token; Connect requires a public address.
- When a token cannot be renewed, its server's tools drop out of conversations until someone reconnects it. The integrations page is the one place that shows `needs_reconnect`.
- OAuth handshakes and client registrations live in the Django cache (Redis), so flushing it aborts flows in progress and forgets registrations.
- Only agents implementing `aget_answer` receive MCP tools. A new agent type has to implement it to use them.
