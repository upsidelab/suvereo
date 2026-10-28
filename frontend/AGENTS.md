# Frontend

The management platform for Suvereo: an admin-panel-style UI for configuring data sets, agents and integrations, managing users, groups and roles with granular permissions, and chatting with agents. It talks to the server API.

React 18 + TypeScript + Vite + Tailwind. Run commands from `frontend/` with pnpm.

## Commands

- Install: `pnpm install`
- Dev server: `pnpm run dev` (needs `VITE_API_BASE` and `VITE_WS_BASE`)
- Build (type-check + bundle): `pnpm build`
- Lint: `pnpm run lint`, fix: `pnpm run lint:fix`

## Structure

- `src/main.tsx` — routes (`createBrowserRouter`) and the `protectedLoginLoader` that redirects unauthenticated users; `src/App.tsx` — authenticated layout with `ApplicationContextProvider` and sidebar
- `src/pages/` — route components, laid out like the URLs (`data-sets/(id)/...`). A page is thin: it composes `PageMain`, `PageHeading` and one feature component.
- `src/components/<feature>/` — feature components, with their hooks in `hooks/`
- `src/components/util/` — shared building blocks (`PageMain`, `PageHeading`, `PaginatedTable`, `EmptyState`, `SkeletonLoader`, `RequirePermission`)
- `src/components/ui/` — Radix primitives and generic form/modal components styled with Tailwind (excluded from ESLint)
- `src/lib/api.ts` and `src/lib/api/` — the API client; `src/lib/types.ts` — shared domain types
- `src/lib/permissions/` — permission codes and role-form logic
- `src/lib/application-context.ts`, `use-application-context.ts` — shared state: data sets, current data set, available agents, account
- `src/lib/authentication-provider.ts` — JWT access and refresh tokens
- Forms use React Hook Form + Zod. Path alias `@/*` maps to `src/*`.

## Permissions

The server decides what is allowed; the frontend only hides what the user cannot use.

- Use the `PERMISSIONS` constants from `src/lib/permissions/codes.ts`, never string literals. They mirror the server's public permission codes.
- Gate routes in `main.tsx` with `RequirePermission` (`globalAnyOf`, `dataSetAnyOf`, `dataSetAccess`). It renders the not-found page and mounts nothing when access is missing.
- Gate controls (buttons, menu items, table actions) with `hasPermission(code)` for global permissions and `hasDataSetPermission(code)` for the current data set, both from `useApplicationContext()`. Permissions are already loaded in the context; do not fetch them again.
- A global permission and a data-set permission are not interchangeable. Use the one that matches how the server scopes the resource.

## API client

- Call the server only through `ApiClient` (`src/lib/api.ts`) and its per-resource sub-clients (`api.dataSets()`, `api.agents()`, …). Do not call `fetch` from components.
- Add a new endpoint as a method on the matching sub-client in `src/lib/api/`, extending `BaseApiClient`, which handles auth headers and token refresh. A new resource gets a new sub-client, registered in `ApiClient`.
- Sub-clients take the server's snake_case responses and return camelCase domain types; keep that mapping in the sub-client (see `toGroupOption` in `src/lib/api/groups.ts`).
- A module creates its client with `new ApiClient(authenticationProviderInstance)`.

## UI consistency

- Reuse before creating: look in `src/components/util/` and `src/components/ui/` first. Do not hand-roll a table, modal, empty state, loader or page heading that already exists.
- Every page uses `PageMain` and `PageHeading`; lists use `PaginatedTable`; empty lists use `EmptyState`; forms in dialogs use `FormModal`; destructive actions use a confirmation modal (see `agents-table/delete-confirmation-modal.tsx`).
- Style with Tailwind and the existing `ui` components; merge class names with `cn` from `src/lib/utils.ts`. Do not add new UI libraries or one-off styles.
- Reference implementations: a simple page `src/pages/users/index.tsx` with `src/components/users/users-list.tsx`; a full CRUD feature `src/components/agents-table/`.
