# Configuration

Apple Juicer reads configuration from Pydantic settings defined in `core/config/settings.py`. All environment variables share the `APPLE_JUICER_` prefix and support nested keys using double underscores. (@core/config/settings.py#10-68)

## Settings Matrix

| Variable | Description | Default |
| --- | --- | --- |
| `APPLE_JUICER_ENVIRONMENT` | Environment label (`development`, `production`). | `development` |
| `APPLE_JUICER_SECURITY__API_TOKEN` | Shared secret required by the frontend via `X-API-Token`. | `dev-token` |
| `APPLE_JUICER_SECURITY__TRUSTED_HOSTS` | Comma-separated origins allowed via CORS. | `http://localhost:5173,http://127.0.0.1:5173,localhost` |
| `APPLE_JUICER_POSTGRES__DSN` | Async SQLAlchemy DSN for persistence. | `sqlite+aiosqlite:///./temp_data/apple_juicer.db` |
| `APPLE_JUICER_REDIS__URL` | Redis connection string for queues and workers. | `redis://localhost:6379/0` |
| `APPLE_JUICER_BACKUP_PATHS__BASE_PATH` | Root directory containing Finder/iTunes backups. | `/data/ios_backups` |
| `APPLE_JUICER_BACKUP_PATHS__TEMP_PATH` | Writable temp directory for decrypted extracts. | `/tmp/apple_juicer` |
| `APPLE_JUICER_BACKUP_PATHS__DECRYPTED_PATH` | Host path where decrypted files are stored. | `/data/decrypted_backups` |
| `APPLE_JUICER_BACKUP_PATHS__HOST_DISPLAY_PATH` | Optional path displayed in the UI. | `None` |
| `APPLE_JUICER_FRONTEND_BASE_URL` | Absolute URL used for constructing frontend links in notifications. | `None` |

### Nested arrays/dicts

Use indexed variables for list-like settings. For example:

```bash
APPLE_JUICER_SECURITY__TRUSTED_HOSTS__0=https://ui.example.com
APPLE_JUICER_SECURITY__TRUSTED_HOSTS__1=https://admin.example.com
```

Pydantic will coerce dictionaries and comma-separated strings into actual lists via the `trusted_hosts` validator. (@core/config/settings.py#10-35)

## Secrets

- Store API tokens and database credentials in a `.env` file next to `docker-compose.yml` or inject them through your orchestrator.
- Avoid hardcoding unlock passphrases; the backend only stores passphrases in memory for the lifetime of a session.

## Docker Compose Overrides

`docker-compose.yml` demonstrates how to pass the required `APPLE_JUICER_*` variables to backend and worker containers. Update the `volumes` section if your backups live elsewhere, and keep mounts read-only for safety. (@docker-compose.yml#3-69)

## Local Development

Create a `.env` file for uvicorn and the worker:

```env
APPLE_JUICER_SECURITY__API_TOKEN=dev-token
APPLE_JUICER_POSTGRES__DSN=postgresql+asyncpg://postgres:postgres@localhost:5432/apple_juicer
APPLE_JUICER_REDIS__URL=redis://localhost:6379/0
APPLE_JUICER_BACKUP_PATHS__BASE_PATH=/Users/me/Library/Application Support/MobileSync/Backup
```

The file is picked up automatically because `AppSettings.model_config.env_file` includes `.env`. (@core/config/settings.py#50-58)

## Observability

Set `LOG_LEVEL=debug` (FastAPI) or `RQ_WORKER_LOG_LEVEL=DEBUG` to increase verbosity when diagnosing discovery/indexing.

For structured logging, wrap `uvicorn` with `--log-config` pointing at a JSON logging configuration.
