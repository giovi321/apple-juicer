---
title: "Security"
description: "The threat model, the deliberate trade-offs of a local tool, and how to compensate if you deploy beyond a workstation."
---

Apple Juicer is built for one investigator on a trusted machine, and its security posture reflects that. The defaults are deliberately light: a single static token, plaintext decrypted data on disk, in-memory sessions. None of that is an accident, and none of it is safe to expose to the public internet. This page lists every trade-off plainly so you can decide what to harden for your deployment.

:::danger[Do not bind this to a public IP]
Run Apple Juicer on a trusted LAN, a single-user workstation, or behind a VPN or authenticating reverse proxy. The bundled authentication will not stop a determined attacker who can reach the port.
:::

## What the design already gets right

- **Every route is gated.** All `/backups/*` routes require `X-API-Token`, and the manifest and file routes additionally require a valid `X-Backup-Session`.
- **Secrets stay out of source.** The token, trusted hosts, and database DSNs all come from environment variables with `.env` support. Unlock passphrases are held in memory only for the life of a session.
- **Decrypted extracts are short-lived.** Files pulled for a single download go to a per-request temp directory that a background task deletes once the response finishes. The whole decrypted copy can be removed with `DELETE /backups/{id}/decrypted`.
- **Heavy work is isolated.** Parsing runs in the worker, not the API process, so a slow or crashing parse can't take the API down with it.

## The trade-offs you are accepting

These are real gaps. For a local tool they are acceptable; past that, weigh each one.

| Area | What it is | Why it matters |
|------|------------|----------------|
| Authentication | One static token, no rotation, scoping, or rate limiting | Anyone who learns the token has full access, and nothing slows a guessing attempt |
| Transport | No TLS enforced; the backend serves plain HTTP on `0.0.0.0:8080` | Credentials and decrypted artifacts cross the wire in clear text unless a proxy adds TLS |
| Sessions | `X-Backup-Session` tokens are in-memory, not bound to client IP or user-agent | A stolen session header works until the TTL expires or the backend restarts |
| Data at rest | Decrypted backups are written to disk unencrypted | A host compromise yields plaintext artifacts |
| Audit | No audit trail for unlock, delete, or export | Hard to reconstruct who did what after the fact |
| Supply chain | Dependencies pinned only to lower bounds; no SBOM | A vulnerable transitive package could go unnoticed |
| Token in the browser | The frontend keeps the API token in `localStorage` | A browser compromise leaks the backend credential |

## How to compensate

If you deploy beyond a single workstation, address these roughly in order of payoff:

1. **Put it behind a real front door.** Terminate TLS and add authentication at a reverse proxy (Authentik, Caddy, Traefik). This single step covers transport, authentication, and most of the session risk at once. Set `APPLE_JUICER_SECURITY__TRUSTED_HOSTS` to your actual origins.
2. **Encrypt the decrypted store.** Put `/data/decrypted_backups` on an encrypted volume and restrict it with filesystem permissions. Purge it after use with the delete endpoint.
3. **Add audit logging.** Emit structured logs for unlocks, downloads, and deletes, with passphrases redacted, and ship them somewhere with retention.
4. **Lock down the supply chain.** Keep a lockfile, run `pip-audit` and `npm audit` in CI, and turn on Dependabot or Renovate.
5. **Treat the token as per-session.** Paste it each session rather than persisting it, and clear it on logout.

The first item does most of the work. Once Apple Juicer is reachable only through an authenticating, TLS-terminating proxy on a network you control, the remaining gaps shrink to the data-at-rest and audit items, which the steps above close.
