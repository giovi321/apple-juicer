---
title: "Data Storage"
description: "What lives on the filesystem, in PostgreSQL, and in Redis — and how durable each one is."
---

Apple Juicer keeps state in three places, and they fail differently. The filesystem holds the backups and is the only thing you must back up. PostgreSQL holds everything the worker derives, which you can rebuild by re-indexing. Redis holds the job queue, which you can lose without consequence.

<div class="diagram-frame">
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 400" role="img" aria-label="Apple Juicer storage layers">
  <defs>
    <pattern id="dots-st" width="22" height="22" patternUnits="userSpaceOnUse">
      <circle cx="1" cy="1" r="0.9" fill="rgba(231,229,228,0.06)"/>
    </pattern>
    <style>
      .eb{font-family:'Geist Mono',monospace;font-size:8px;letter-spacing:0.18em;}
      .nm{font-family:'Geist',sans-serif;font-weight:600;font-size:14px;fill:#fafaf9;}
      .it{font-family:'Geist Mono',monospace;font-size:10px;fill:#e7e5e4;}
      .ital{font-family:'Instrument Serif',Georgia,serif;font-style:italic;font-size:12px;fill:#a8a29e;}
    </style>
  </defs>
  <rect width="100%" height="100%" fill="#1c1917"/>
  <rect width="100%" height="100%" fill="url(#dots-st)" opacity="0.6"/>

  <!-- Filesystem -->
  <rect x="40" y="88" width="272" height="248" rx="8" fill="rgba(231,229,228,0.03)" stroke="rgba(231,229,228,0.30)" stroke-width="1"/>
  <text x="64" y="122" class="eb" fill="#78716c">DISK</text>
  <text x="64" y="148" class="nm">Filesystem</text>
  <line x1="64" y1="164" x2="288" y2="164" stroke="rgba(231,229,228,0.12)" stroke-width="0.8"/>
  <text x="64" y="194" class="it">Backups · read-only mount</text>
  <text x="64" y="222" class="it">Temp sandbox · per request</text>
  <text x="64" y="250" class="it">Decrypted store · plaintext</text>
  <line x1="64" y1="280" x2="288" y2="280" stroke="rgba(231,229,228,0.12)" stroke-width="0.8"/>
  <text x="64" y="306" class="ital">Authoritative — back this up</text>

  <!-- PostgreSQL (focal) -->
  <rect x="344" y="88" width="272" height="248" rx="8" fill="rgba(245,158,11,0.10)" stroke="#f59e0b" stroke-width="1.2"/>
  <text x="368" y="122" class="eb" fill="#f59e0b">DATA</text>
  <text x="368" y="148" class="nm">PostgreSQL</text>
  <line x1="368" y1="164" x2="592" y2="164" stroke="rgba(245,158,11,0.30)" stroke-width="0.8"/>
  <text x="368" y="194" class="it">backups · registry + status</text>
  <text x="368" y="222" class="it">artifact tables · 10 types</text>
  <text x="368" y="250" class="it">artifact_search_index</text>
  <line x1="368" y1="280" x2="592" y2="280" stroke="rgba(245,158,11,0.30)" stroke-width="0.8"/>
  <text x="368" y="306" class="ital">Rebuildable — just re-index</text>

  <!-- Redis -->
  <rect x="648" y="88" width="272" height="248" rx="8" fill="rgba(231,229,228,0.05)" stroke="#a8a29e" stroke-width="1"/>
  <text x="672" y="122" class="eb" fill="#a8a29e">QUEUE</text>
  <text x="672" y="148" class="nm">Redis</text>
  <line x1="672" y1="164" x2="896" y2="164" stroke="rgba(231,229,228,0.12)" stroke-width="0.8"/>
  <text x="672" y="194" class="it">RQ default queue</text>
  <text x="672" y="222" class="it">job metadata + heartbeats</text>
  <text x="672" y="250" class="it">no tokens, no payloads</text>
  <line x1="672" y1="280" x2="896" y2="280" stroke="rgba(231,229,228,0.12)" stroke-width="0.8"/>
  <text x="672" y="306" class="ital">Ephemeral — safe to lose</text>
</svg>
</div>

## Filesystem

The backups are the source of truth and nothing copies them wholesale. Two paths matter:

- **Backup data** mounts read-only into the backend and worker (default `./data` → `/data/ios_backups`). Apple Juicer reads it and never writes to it.
- **Temporary sandbox** under `backup_paths.temp_path` (default `/tmp/apple_juicer`) holds files extracted for a single download or parse. A Starlette `BackgroundTask` deletes each one after the response finishes.

Decrypted artifact databases are written to `backup_paths.decrypted_path` so the worker can index them and the UI can serve attachments without re-unlocking every time. That directory is plaintext — see [Security](../../operations/security/).

## PostgreSQL

Postgres is everything the worker derives from a backup:

- **`backups`** — the canonical list of discovered backups with device metadata, size, encryption flag, and the status lifecycle (`DISCOVERED` → `DECRYPTED` → `INDEXING` → `INDEXED`).
- **Artifact tables** — `photo_assets`, `whatsapp_*`, `messages`, `notes`, `calendar_*`, `contacts`, and the rest, one set per artifact type. Every row links back to `backups.id` with `ON DELETE CASCADE`, so deleting a backup cleans up everything it produced.
- **`artifact_search_index`** — one denormalized text row per item, which is what global search queries.

The async SQLAlchemy engine reads its DSN from `APPLE_JUICER_POSTGRES__DSN`, defaulting to `sqlite+aiosqlite:///./temp_data/apple_juicer.db` so the tool runs without Postgres for tests and quick local trials. The schema is created and kept current by Alembic, which runs `upgrade head` automatically on backend startup.

## Redis

Redis does two jobs and stores nothing sensitive:

- **The queue.** `core.queue.get_queue()` returns a cached connection to the `default` queue with a 10-minute job timeout.
- **Job bookkeeping.** RQ keeps its own job metadata, heartbeats, and results here.

Session tokens and decrypted data never touch Redis; they live in memory in the backend and worker processes. Point Redis wherever you like with `APPLE_JUICER_REDIS__URL`.

## Backing it up

The three layers map cleanly onto a recovery plan:

1. **Filesystem** — snapshot or rsync the mounted backup directory. This is the only irreplaceable copy.
2. **PostgreSQL** — use `pg_dump` or `pg_basebackup` if you want to keep the indexes. If you don't, you can drop the database and re-index from the backups.
3. **Redis** — skip it. A lost queue just means re-triggering any indexing run that was in flight.

Because decrypted payloads are never the system of record, recovery comes down to one thing: point the tool back at the backup directory and, if you didn't keep Postgres, re-index.
