# Frontend UI

The frontend lives under `frontend/` and is built with React 18, TypeScript, Vite, Tailwind-esque utility classes, and Radix-inspired primitives. Production builds are emitted by Vite and served via `nginx:alpine` in Docker.

## Project Structure

- `src/App.tsx` – single-page experience orchestrating backup selection, unlock flow, manifest browser, and artifact tabs.
- `src/lib/api.ts` – thin wrapper around `fetch` that injects API/session tokens and exposes typed helper methods.
- `src/lib/types.ts` – shared types mirroring backend schemas, plus view models for artifact renderers.
- `src/components/*` (future) – when the UI grows, extract panels into components here.

## State Machine

1. **Session Setup** – user enters the API token (default `dev-token`), stored in component state and reused for every request.
2. **Backup Selection** – `useEffect` calls `api.listBackups()` (GET `/backups`). The manifest tree stays disabled until a backup is unlocked.
3. **Unlocking** – `api.unlockBackup()` posts the passphrase; on success it returns `session_token` + TTL which the frontend saves to issue `X-Backup-Session` headers.
4. **Manifest Browsing** – the manifest view paginates through `/backups/{id}/files`, allows domain/path filters, and lazy-loads more rows.
5. **Artifact Tabs** – additional tabs (Photos, Messages, WhatsApp, etc.) fire artifact-specific API calls once their data exists in Postgres.

All requests respect the API base URL provided through `import.meta.env.VITE_API_BASE_URL` (set to `http://backend:8080` inside Docker). During local development Vite proxies to `http://localhost:8080`.

## Styling and Layout

- The root layout uses a fixed-width sidebar for backups and a flexible content area for manifest/artifacts.
- Animations and transitions are handled via CSS modules + utility classes included in `src/App.tsx`.
- Nginx injects cache headers so the SPA can be safely served behind reverse proxies.

## Browser Compatibility

The UI targets modern Chromium, Firefox, and Safari releases. It relies on Fetch API, async/await, and CSS grid/flexbox, so no legacy polyfills are included by default.

## Extensibility Tips

- Represent new artifact types in `src/lib/types.ts`, then add view tabs in `App.tsx`.
- If the API surface expands, keep `src/lib/api.ts` as the central spot for fetch wrappers so headers stay consistent.
- For large feature work, consider migrating to React Router and splitting the manifest + artifact states into context providers.
