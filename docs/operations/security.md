# Security Assessment

This report summarizes the current security posture of Apple Juicer based on a review of the FastAPI backend, worker pipeline, and configuration defaults.

## Strengths

- **Header-based access control** – Every `/backups/*` route enforces both `X-API-Token` and, when appropriate, `X-Backup-Session` headers via `require_api_token` and `require_session_token`. @api/security.py#8-21 @api/routes/backups.py#26-341
- **Environment-managed secrets** – Sensitive values (API token, trusted hosts, Redis/Postgres DSNs) flow exclusively through Pydantic settings with `.env` support and nested prefixes, keeping credentials out of source. @core/config/settings.py#10-73
- **Ephemeral decrypted data** – Temporary extraction paths are scoped per request and automatically cleaned by `BackgroundTask` callbacks; decrypted payloads can be purged via `DELETE /{backup_id}/decrypted`. @api/routes/backups.py#122-225
- **Parser isolation** – Artifact indexing runs inside a worker queue, limiting long-running or CPU-heavy operations inside the API process. @api/routes/backups.py#109-158

## Risks & Gaps

| Area | Observation | Impact |
| --- | --- | --- |
| Authentication | The API uses a single static bearer token with no rotation, scoping, or brute-force protection. | Token disclosure compromises the entire deployment; no rate limiting to slow spray attempts. |
| Transport security | TLS termination is assumed but not enforced; the backend will happily serve HTTP on `0.0.0.0:8080`. | Credentials and decrypted artifacts can transit in clear text if deployed behind misconfigured proxies. |
| Session handling | `X-Backup-Session` tokens are generated in-memory; there is no expiration enforcement beyond TTL metadata, revocation persistence, or binding to client attributes (IP/User-Agent). | Stolen session headers remain valid until the worker restarts or TTL expires. |
| Secrets at rest | Decrypted backups are written to host paths (`/data/decrypted_backups`) without encryption at rest or filesystem ACL guidance. | Host compromise yields full plaintext artifacts and secrets. |
| Logging & audit | There is no audit trail for administrative actions (unlock, delete, export), and log sanitization is ad hoc. | Difficult to investigate insider misuse or external compromise. |
| Supply chain | Dependencies (FastAPI, RQ, iphone-backup-decrypt) are unpinned beyond semver lower bounds; no SBOM or vulnerability scanning is documented. | Increases risk of unnoticed vulnerable transitive packages. |
| Frontend token storage | The frontend stores `X-API-Token` client-side (local state) without browser storage hardening guidance. | Browser compromise exposes backend credentials.

## Recommendations

1. **Strengthen authentication**
   - Replace the single static token with per-user API keys or OAuth2 flows with revocation and rotation.
   - Add rate limiting (e.g., `slowapi`) and lockout alerts for repeated failures.
2. **Enforce transport security**
   - Require HTTPS by default (e.g., behind Traefik/Caddy) and document TLS termination expectations clearly.
   - Set `APPLE_JUICER_SECURITY__TRUSTED_HOSTS` to production origins only.
3. **Harden session management**
   - Persist session tokens with short expirations and bind them to client metadata; consider signed JWTs with HMAC rotation.
   - Provide an admin endpoint to enumerate and revoke active sessions.
4. **Protect decrypted artifacts**
   - Encrypt `/data/decrypted_backups` at rest or mount it on encrypted volumes; isolate via POSIX permissions.
   - Offer a configuration flag to automatically purge decrypted data after download.
5. **Improve observability**
   - Emit structured audit logs for unlocks, downloads, and data purges, redacting passphrases.
   - Integrate with a SIEM or at least ship logs to centralized storage with retention policies.
6. **Secure the supply chain**
   - Pin dependencies (Poetry/uv lockfile), produce an SBOM, and run `pip-audit` / `npm audit` in CI.
   - Enable Dependabot or Renovate for timely patching.
7. **Frontend handling guidance**
   - Document that API tokens should be pasted per-session only and never stored in browser persistence; consider adding an unlock modal that avoids `localStorage` entirely.
8. **Operational safeguards**
   - Provide IaC snippets (Docker Compose override examples) that set unique secrets, enable TLS, and restrict network exposure to the LAN.

Addressing these items will materially improve confidentiality of decrypted backups, resilience against credential theft, and forensic readiness.
