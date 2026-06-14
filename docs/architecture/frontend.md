# Frontend UI

The frontend lives under `frontend/` and is built with React 19, TypeScript, and
Vite 7. Styling is plain, hand-written CSS (no Tailwind or component library).
Production builds are emitted by Vite and served via `nginx:alpine` in Docker.

## Project Structure

- `src/main.tsx` – entry point; mounts the app and wraps it in a top-level `ErrorBoundary`.
- `src/AppNew.tsx` – root component that drives the app state machine (token → backup selection → decrypt/unlock → explorer).
- `src/pages/` – screen-level components: `BackupSelector`, `PasswordPrompt`, and `Explorer`.
- `src/pages/modules/` – the per-artifact modules rendered inside the Explorer (`FilesModule`, `WhatsAppModule`, `MessagesModule`, the tabular `*Tab` components, `SearchTab`, `TimelineTab`) plus the shared `Attachment` renderer.
- `src/components/` – cross-cutting components such as `ErrorBoundary`.
- `src/lib/` – `api.ts` (typed `fetch` wrapper that injects API/session tokens), `types.ts` (types mirroring backend schemas), `csv.ts` (client-side CSV export), and `useLocalStorage`.
- `src/styles/` – component CSS (e.g. `Explorer.css`).

## State Machine

`AppNew` advances through four states:

1. **Token input** – the user enters the API token (default `dev-token`); it is persisted in `localStorage` and reused for every request.
2. **Backup selection** – `api.listBackups()` (GET `/backups`) lists discovered backups. Selecting an already-decrypted backup jumps straight to the explorer; otherwise the password prompt is shown.
3. **Decrypt & unlock** – decryption runs as a background worker job; the UI stays responsive and polls `getDecryptStatus` until the backup reaches `decrypted` (or `failed`). On success the backup is also unlocked, yielding a `session_token` (used for `X-Backup-Session`) saved per backup in `localStorage`.
4. **Explorer** – a tabbed view over the decrypted backup.

## Explorer

`Explorer` is a thin shell: it renders the module tab bar and delegates to one
self-contained module at a time. Each module owns its own data fetching,
pagination, search, and (for conversations) the unlock prompt, extraction
overlay, and image preview. The shell wraps the active module in an
`ErrorBoundary` keyed by the active tab, so a crash in one module shows an
inline fallback and switching tabs recovers automatically rather than
white-screening the app. Global-search results deep-link into a conversation via
an `initialSelectedGuid` prop on the WhatsApp/Messages modules.

All requests respect the API base URL provided through
`import.meta.env.VITE_API_BASE_URL` (set to the backend in Docker); during local
development Vite proxies to the backend on port `8080`.

## Testing

Component behaviour is covered by Vitest + React Testing Library (jsdom). Notable
suites: `Explorer.test.tsx` characterizes the WhatsApp/Messages conversation
flows (the regression guard for the module split) and `ErrorBoundary.test.tsx`
covers the fallback/reset behaviour. Run with `npm run test`.

## Browser Compatibility

The UI targets modern Chromium, Firefox, and Safari releases. It relies on the
Fetch API, async/await, IntersectionObserver, and CSS grid/flexbox, so no legacy
polyfills are included by default.

## Extensibility Tips

- Adding an artifact type is two halves: register an `ArtifactSpec` on the backend, then add a frontend module under `src/pages/modules/`, wire it into `Explorer`'s tab list, add a typed helper in `src/lib/api.ts`, and a type in `src/lib/types.ts`.
- Keep `src/lib/api.ts` as the central spot for fetch wrappers so API/session headers stay consistent.
- Reuse the shared `Attachment` component for any module that renders message attachments.
