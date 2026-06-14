---
title: "Worker Pipeline"
description: "How the RQ worker decrypts a backup and indexes its artifacts into Postgres."
---

The worker exists to keep slow work out of the API process. It is an RQ consumer that pulls a job off Redis, runs it to completion, and updates the backup's status as it goes. It shares the backend's Docker image and virtualenv, so every parser and database model is already on hand.

The indexing job does the same thing for every backup: mark it busy, clear any previous rows, then loop over the artifact registry, parsing each SQLite database it finds and writing normalized rows plus search entries.

<div class="diagram-frame">
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 420" role="img" aria-label="Worker indexing job pipeline">
  <defs>
    <pattern id="dots-wk" width="22" height="22" patternUnits="userSpaceOnUse">
      <circle cx="1" cy="1" r="0.9" fill="rgba(231,229,228,0.06)"/>
    </pattern>
    <marker id="arw" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
      <polygon points="0 0, 8 3, 0 6" fill="#a8a29e"/>
    </marker>
    <marker id="arw-accent" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
      <polygon points="0 0, 8 3, 0 6" fill="#f59e0b"/>
    </marker>
    <style>
      .eb{font-family:'Geist Mono',monospace;font-size:8px;letter-spacing:0.18em;fill:#78716c;}
      .nm{font-family:'Geist',sans-serif;font-weight:600;font-size:12px;fill:#fafaf9;}
      .sb{font-family:'Geist Mono',monospace;font-size:9px;fill:#a8a29e;}
      .lb{font-family:'Geist Mono',monospace;font-size:8px;fill:#a8a29e;letter-spacing:0.06em;}
      .lba{font-family:'Geist Mono',monospace;font-size:8px;fill:#f59e0b;letter-spacing:0.06em;}
      .cp{font-family:'Geist Mono',monospace;font-size:7px;letter-spacing:0.08em;}
    </style>
  </defs>
  <rect width="100%" height="100%" fill="#1c1917"/>
  <rect width="100%" height="100%" fill="url(#dots-wk)" opacity="0.6"/>
  <text x="40" y="56" class="eb">WORKER · INDEX JOB</text>

  <!-- outer arrows -->
  <line x1="180" y1="244" x2="232" y2="244" stroke="#a8a29e" stroke-width="1" marker-end="url(#arw)"/>
  <line x1="384" y1="244" x2="432" y2="244" stroke="#a8a29e" stroke-width="1" marker-end="url(#arw)"/>
  <line x1="744" y1="244" x2="792" y2="244" stroke="#f59e0b" stroke-width="1.2" marker-end="url(#arw-accent)"/>
  <rect x="388" y="222" width="44" height="12" rx="2" fill="#1c1917"/>
  <text x="410" y="231" class="lb" text-anchor="middle">BEGIN</text>
  <rect x="748" y="222" width="44" height="12" rx="2" fill="#1c1917"/>
  <text x="770" y="231" class="lba" text-anchor="middle">COMMIT</text>

  <!-- Job -->
  <rect x="40" y="212" width="140" height="64" rx="6" fill="rgba(231,229,228,0.04)" stroke="#78716c" stroke-width="1"/>
  <rect x="48" y="220" width="44" height="12" rx="2" fill="transparent" stroke="rgba(120,113,108,0.55)" stroke-width="0.8"/>
  <text x="70" y="229" class="cp" fill="#a8a29e" text-anchor="middle">QUEUE</text>
  <text x="110" y="252" class="nm" text-anchor="middle">Job popped</text>

  <!-- Mark INDEXING -->
  <rect x="232" y="212" width="152" height="64" rx="6" fill="rgba(231,229,228,0.05)" stroke="#a8a29e" stroke-width="1"/>
  <rect x="240" y="220" width="44" height="12" rx="2" fill="transparent" stroke="rgba(168,162,158,0.55)" stroke-width="0.8"/>
  <text x="262" y="229" class="cp" fill="#a8a29e" text-anchor="middle">STATE</text>
  <text x="308" y="248" class="nm" text-anchor="middle">INDEXING</text>
  <text x="308" y="264" class="sb" text-anchor="middle">truncate old rows</text>

  <!-- Registry loop container (focal) -->
  <rect x="432" y="128" width="312" height="192" rx="8" fill="rgba(245,158,11,0.06)" stroke="#f59e0b" stroke-width="1.2" stroke-dasharray="4,4"/>
  <text x="452" y="152" class="lba">REGISTRY · 10 ARTIFACT SPECS</text>

  <!-- loop arrow -->
  <path d="M 664 212 C 664 184, 516 184, 516 212" fill="none" stroke="#f59e0b" stroke-width="1" marker-end="url(#arw-accent)"/>
  <rect x="556" y="178" width="68" height="12" rx="2" fill="#1c1917"/>
  <text x="590" y="187" class="lba" text-anchor="middle">× EACH SPEC</text>

  <!-- inner: parse -->
  <rect x="452" y="216" width="128" height="64" rx="6" fill="rgba(231,229,228,0.06)" stroke="#a8a29e" stroke-width="1"/>
  <text x="516" y="246" class="nm" text-anchor="middle">parse(db)</text>
  <text x="516" y="262" class="sb" text-anchor="middle">read SQLite</text>

  <!-- inner: ingest -->
  <line x1="580" y1="248" x2="600" y2="248" stroke="#a8a29e" stroke-width="1" marker-end="url(#arw)"/>
  <rect x="600" y="216" width="128" height="64" rx="6" fill="rgba(231,229,228,0.06)" stroke="#a8a29e" stroke-width="1"/>
  <text x="664" y="242" class="nm" text-anchor="middle">ingest</text>
  <text x="664" y="258" class="sb" text-anchor="middle">rows + search</text>

  <!-- Mark INDEXED -->
  <rect x="792" y="212" width="152" height="64" rx="6" fill="rgba(231,229,228,0.05)" stroke="#a8a29e" stroke-width="1"/>
  <rect x="800" y="220" width="44" height="12" rx="2" fill="transparent" stroke="rgba(168,162,158,0.55)" stroke-width="0.8"/>
  <text x="822" y="229" class="cp" fill="#a8a29e" text-anchor="middle">STATE</text>
  <text x="868" y="252" class="nm" text-anchor="middle">INDEXED</text>

  <line x1="40" y1="372" x2="960" y2="372" stroke="rgba(231,229,228,0.10)" stroke-width="0.8"/>
  <text x="40" y="390" class="lba">DASHED AMBER = one loop over the artifact registry</text>
</svg>
</div>

## Running the worker

The worker is plain RQ on the `default` queue. Both of these start one:

```bash
rq worker default --url redis://localhost:6379/0
# or the console script from pyproject.toml:
apple-juicer-worker
```

It reads the Redis DSN from `APPLE_JUICER_REDIS__URL`. Run it inside the same virtualenv as the backend so the parsers and SQLAlchemy models resolve.

## The job, step by step

The backend enqueues `index_backup_job`, the sync wrapper that runs the async job under `asyncio.run`. Enqueuing the coroutine directly was the original bug that made indexing silently do nothing; the wrapper is what RQ actually calls. Once a worker picks it up, it:

1. Sets the backup's status to `INDEXING`.
2. Truncates any artifact rows left from a previous run, so a re-index is always clean.
3. Loops over the artifact registry. For each registered type whose database is present, it parses the SQLite file and writes normalized rows plus entries in `ArtifactSearchIndex`.
4. Sets the status to `INDEXED` and commits.

Adding a new artifact type means registering one `ArtifactSpec`. The worker picks it up on the next run with no other changes — there is no per-type code in the job itself. See [Data Storage](../storage/) and the [Directory Layout](../../reference/directory-layout/) for where a spec lives.

## What each parser reads

Every module in `parsers/` reads one SQLite database copied out of the backup and returns records the registry ingests:

| Parser | Source database | Produces |
|--------|-----------------|----------|
| `parsers/photos.py` | `Photos.sqlite` | Photo assets |
| `parsers/messages.py` | `chat.db` | iMessage/SMS conversations, messages, attachments |
| `parsers/whatsapp.py` | `ChatStorage.sqlite` | WhatsApp chats, messages, attachments |
| `parsers/notes.py` | `NoteStore.sqlite` | Notes |
| `parsers/calendar.py` | `Calendar.sqlitedb` | Calendars and events |
| `parsers/contacts.py` | `AddressBook.sqlitedb` | Contacts |
| `parsers/calls.py` | `CallHistory.storedata` | Call records |
| `parsers/safari.py` | `History.db` | Safari visits |
| `parsers/locations.py` | `routined` caches | Significant locations |
| `parsers/voicemail.py` | `voicemail.db` | Voicemails |

A parser whose source database is missing returns nothing and the loop moves on, so a backup that never used WhatsApp simply indexes without it. Two sources are flaky by nature: the `routined` location cache is often excluded from backups, and Safari's `History.db` domain shifts between iOS versions. Both parsers are written defensively and will leave their views empty rather than fail the job.

## Errors, retries, and scaling

A fatal error bubbles up to RQ. Pass `--max-retries` or `--retry-interval` when enqueuing if you want automatic retries; otherwise re-running the job is safe because it truncates first. Logs go to the `worker` logger, which Docker Compose surfaces in the `worker` container output.

To index faster, run more workers — add replicas in `docker-compose.yml` or use `docker compose up --scale worker=3`. Every job targets a single backup, so workers never collide on the `default` queue.
