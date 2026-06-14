---
title: "Frontend UI"
description: "React 19 + Vite + plain CSS. A four-state app shell that hands off to self-contained per-artifact modules."
---

The frontend lives under `frontend/` and is built with React 19, TypeScript, and Vite 7. The styling is hand-written CSS — no Tailwind, no component library. Vite emits the production build and nginx serves it in Docker.

## How the code is laid out

- `src/main.tsx` — the entry point. Mounts the app inside a top-level `ErrorBoundary`.
- `src/AppNew.tsx` — the root component that drives the app state machine.
- `src/pages/` — the screen-level components: `BackupSelector`, `PasswordPrompt`, and `Explorer`.
- `src/pages/modules/` — the per-artifact modules the Explorer renders (`FilesModule`, `WhatsAppModule`, `MessagesModule`, the tabular `*Tab` components, `SearchTab`, `TimelineTab`) plus the shared `Attachment` renderer.
- `src/components/` — cross-cutting components such as `ErrorBoundary`.
- `src/lib/` — `api.ts` (the typed `fetch` wrapper), `types.ts` (types mirroring the backend schemas), `csv.ts` (client-side CSV export), and `useLocalStorage`.
- `src/styles/` — component CSS such as `Explorer.css`.

## The four states

`AppNew` walks through four states, and the token plus per-backup session tokens persist in `localStorage`:

1. **Token input.** You enter the API token (default `dev-token`). Every request reuses it.
2. **Backup selection.** `api.listBackups()` lists what was discovered. Picking a decrypted backup jumps to the explorer; otherwise the password prompt appears.
3. **Decrypt and unlock.** Decryption runs as a worker job. The UI stays responsive and polls `getDecryptStatus` until the backup reaches `decrypted` or `failed`. On success it also unlocks, producing the session token used for attachment downloads.
4. **Explorer.** The tabbed view over a decrypted backup.

## The Explorer is a shell

`Explorer` renders the tab bar and hands off to one module at a time. Each module owns its own data fetching, pagination, search, and — for conversations — the unlock prompt, the extraction overlay, and the image preview. The shell wraps the active module in an `ErrorBoundary` keyed by the active tab, so a crash in one module shows an inline fallback and switching tabs recovers instead of blanking the whole app. Search results deep-link into a conversation through an `initialSelectedGuid` prop on the WhatsApp and Messages modules.

API calls use the base URL from `import.meta.env.VITE_API_BASE_URL` (the backend, in Docker). During local development Vite proxies to the backend on port 8080.

## Tests

Component behavior is covered by Vitest with React Testing Library and jsdom. Two suites carry most of the weight: `Explorer.test.tsx` pins the WhatsApp and Messages conversation flows — it was the regression guard for splitting those modules out — and `ErrorBoundary.test.tsx` covers the fallback and reset behavior. Run them with `npm run test`.

## Adding an artifact type

A new type is two halves. On the backend, register an `ArtifactSpec`. On the frontend, add a module under `src/pages/modules/`, wire it into the Explorer tab list, add a typed helper in `src/lib/api.ts`, and a type in `src/lib/types.ts`. Reuse the shared `Attachment` component for anything that renders message attachments.
