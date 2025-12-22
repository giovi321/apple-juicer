# Worker Pipeline

The worker is a lightweight RQ consumer that offloads CPU/IO-intensive artifact parsing from the FastAPI process. It shares the same Docker image and virtualenv, ensuring access to parsers and database models.

## Entry Point

- Command: `rq worker default --url redis://...`
- Alternatively: `ios-backup-worker` console script (defined in `pyproject.toml`) that wraps `rq worker`.

The worker connects to Redis using the DSN from `IOS_BACKUP_REDIS__URL`. (@core/queue.py#11-24)

## Job Lifecycle

1. Backend enqueues a job by calling `core.queue.get_queue().enqueue(index_backup_job, ...)`.
2. Worker pops the job and executes `worker.tasks.index_backup_job`, which runs the async `_index_backup_job` coroutine inside `asyncio.run`. (@worker/tasks.py#40-342)
3. Job steps:
   - Update the `backups.status` column to `INDEXING`.
   - Truncate previous artifact rows for the backup.
   - Parse and ingest artifacts domain-by-domain (Photos, WhatsApp, Messages, Notes, Calendar, Contacts).
   - Populate `ArtifactSearchIndex` for cross-artifact search.
   - Mark backup as `INDEXED` and commit.

## Parsers

Each parser module in `parsers/` reads the SQLite database copied from the backup payload:

| Parser | Source DB | Output tables |
| --- | --- | --- |
| `parsers/photos.py` | `Photos.sqlite` | `PhotoAsset`, `ArtifactSearchIndex` |
| `parsers/messages.py` | `chat.db` | `MessageConversation`, `Message`, `MessageAttachment` |
| `parsers/whatsapp.py` | `ChatStorage.sqlite` | `WhatsAppChat`, `WhatsAppMessage`, `WhatsAppAttachment` |
| `parsers/notes.py` | `NoteStore.sqlite` | `Note` |
| `parsers/calendar.py` | `Calendar.sqlitedb` | `Calendar`, `CalendarEvent` |
| `parsers/contacts.py` | `AddressBook.sqlitedb` | `Contact` |

The job receives a mapping of logical artifact names → paths so each parser can skip absent files gracefully.

## Error Handling & Retries

- Missing artifact files are simply ignored (parser returns early).
- Fatal errors bubble up to RQ; configure `--max-retries` or `--retry-interval` when enqueuing if desired.
- Logs are emitted via the `worker` logger; Docker Compose surfaces them in `worker-1` container output.

## Scaling

Run multiple worker replicas by adding more services in `docker-compose.yml` or using `docker compose up --scale worker=3`. All workers can safely consume from the `default` queue because each job targets a distinct backup identifier.
