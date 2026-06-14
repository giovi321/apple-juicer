---
title: "Architecture Overview"
description: "The five services that make up Apple Juicer and how a backup flows through them."
---

Apple Juicer runs as five services behind Docker Compose. The FastAPI backend is the hub: the browser talks to it, it owns the database and the job queue, and it mounts the backups read-only. The slow work — decrypting and parsing — runs in a separate RQ worker so the API never blocks on it.

<div class="diagram-frame">
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1040 560" role="img" aria-label="Apple Juicer service architecture">
  <defs>
    <pattern id="dots-arch" width="22" height="22" patternUnits="userSpaceOnUse">
      <circle cx="1" cy="1" r="0.9" fill="rgba(231,229,228,0.06)"/>
    </pattern>
    <marker id="arr" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
      <polygon points="0 0, 8 3, 0 6" fill="#a8a29e"/>
    </marker>
    <marker id="arr-accent" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
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
  <rect width="100%" height="100%" fill="url(#dots-arch)" opacity="0.6"/>

  <text x="40" y="60" class="eb">CLIENT</text>
  <text x="392" y="60" class="eb">SERVER</text>
  <text x="724" y="60" class="eb">QUEUE · STORES</text>
  <text x="568" y="540" class="eb">DISK (READ-ONLY)</text>

  <!-- arrows first -->
  <line x1="152" y1="276" x2="192" y2="276" stroke="#a8a29e" stroke-width="1" marker-end="url(#arr)"/>
  <line x1="328" y1="276" x2="380" y2="252" stroke="#a8a29e" stroke-width="1" marker-end="url(#arr)"/>
  <line x1="540" y1="196" x2="720" y2="196" stroke="#a8a29e" stroke-width="1" marker-end="url(#arr)"/>
  <line x1="796" y1="232" x2="796" y2="320" stroke="#f59e0b" stroke-width="1.2" marker-end="url(#arr-accent)"/>
  <line x1="720" y1="356" x2="544" y2="356" stroke="#a8a29e" stroke-width="1" marker-end="url(#arr)"/>
  <line x1="460" y1="256" x2="460" y2="320" stroke="#a8a29e" stroke-width="1" marker-end="url(#arr)"/>
  <line x1="744" y1="392" x2="708" y2="420" stroke="#a8a29e" stroke-width="1" marker-end="url(#arr)"/>
  <line x1="512" y1="256" x2="600" y2="420" stroke="#a8a29e" stroke-width="1" stroke-dasharray="5,4" marker-end="url(#arr)"/>

  <!-- arrow labels -->
  <rect x="320" y="246" width="40" height="12" rx="2" fill="#1c1917"/>
  <text x="340" y="255" class="lb" text-anchor="middle">FETCH</text>
  <rect x="586" y="184" width="52" height="12" rx="2" fill="#1c1917"/>
  <text x="612" y="193" class="lb" text-anchor="middle">ENQUEUE</text>
  <rect x="804" y="270" width="56" height="12" rx="2" fill="#1c1917"/>
  <text x="832" y="279" class="lba" text-anchor="middle">DISPATCH</text>
  <rect x="600" y="344" width="40" height="12" rx="2" fill="#1c1917"/>
  <text x="620" y="353" class="lb" text-anchor="middle">WRITE</text>
  <rect x="468" y="282" width="28" height="12" rx="2" fill="#1c1917"/>
  <text x="482" y="291" class="lb" text-anchor="middle">SQL</text>
  <rect x="700" y="398" width="36" height="12" rx="2" fill="#1c1917"/>
  <text x="718" y="407" class="lb" text-anchor="middle">READ</text>
  <rect x="520" y="330" width="64" height="12" rx="2" fill="#1c1917"/>
  <text x="552" y="339" class="lb" text-anchor="middle">DOWNLOAD</text>

  <!-- Browser -->
  <rect x="40" y="240" width="112" height="72" rx="6" fill="rgba(231,229,228,0.04)" stroke="#78716c" stroke-width="1"/>
  <rect x="48" y="248" width="36" height="12" rx="2" fill="transparent" stroke="rgba(120,113,108,0.55)" stroke-width="0.8"/>
  <text x="66" y="257" class="cp" fill="#a8a29e" text-anchor="middle">USER</text>
  <text x="96" y="288" class="nm" text-anchor="middle">Browser</text>

  <!-- Frontend -->
  <rect x="192" y="240" width="136" height="72" rx="6" fill="rgba(231,229,228,0.06)" stroke="#a8a29e" stroke-width="1"/>
  <rect x="200" y="248" width="32" height="12" rx="2" fill="transparent" stroke="rgba(168,162,158,0.55)" stroke-width="0.8"/>
  <text x="216" y="257" class="cp" fill="#a8a29e" text-anchor="middle">SPA</text>
  <text x="260" y="282" class="nm" text-anchor="middle">Frontend</text>
  <text x="260" y="298" class="sb" text-anchor="middle">nginx + React</text>

  <!-- Backend (focal) -->
  <rect x="380" y="160" width="160" height="96" rx="6" fill="rgba(245,158,11,0.14)" stroke="#f59e0b" stroke-width="1.2"/>
  <rect x="388" y="168" width="32" height="12" rx="2" fill="transparent" stroke="rgba(245,158,11,0.55)" stroke-width="0.8"/>
  <text x="404" y="177" class="cp" fill="#f59e0b" text-anchor="middle">API</text>
  <text x="460" y="206" class="nm" text-anchor="middle">FastAPI backend</text>
  <text x="460" y="222" class="sb" text-anchor="middle">routers + services</text>
  <text x="460" y="238" class="sb" text-anchor="middle">async SQLAlchemy</text>

  <!-- Redis -->
  <rect x="720" y="160" width="152" height="72" rx="6" fill="rgba(231,229,228,0.05)" stroke="#a8a29e" stroke-width="1"/>
  <rect x="728" y="168" width="44" height="12" rx="2" fill="transparent" stroke="rgba(168,162,158,0.55)" stroke-width="0.8"/>
  <text x="750" y="177" class="cp" fill="#a8a29e" text-anchor="middle">QUEUE</text>
  <text x="796" y="202" class="nm" text-anchor="middle">Redis</text>
  <text x="796" y="218" class="sb" text-anchor="middle">RQ · default</text>

  <!-- Worker -->
  <rect x="720" y="320" width="152" height="72" rx="6" fill="rgba(231,229,228,0.06)" stroke="#a8a29e" stroke-width="1"/>
  <rect x="728" y="328" width="52" height="12" rx="2" fill="transparent" stroke="rgba(168,162,158,0.55)" stroke-width="0.8"/>
  <text x="754" y="337" class="cp" fill="#a8a29e" text-anchor="middle">WORKER</text>
  <text x="796" y="362" class="nm" text-anchor="middle">RQ worker</text>
  <text x="796" y="378" class="sb" text-anchor="middle">decrypt + parse</text>

  <!-- Postgres -->
  <rect x="380" y="320" width="160" height="72" rx="6" fill="rgba(231,229,228,0.05)" stroke="#a8a29e" stroke-width="1"/>
  <rect x="388" y="328" width="36" height="12" rx="2" fill="transparent" stroke="rgba(168,162,158,0.55)" stroke-width="0.8"/>
  <text x="406" y="337" class="cp" fill="#a8a29e" text-anchor="middle">DATA</text>
  <text x="460" y="362" class="nm" text-anchor="middle">PostgreSQL</text>
  <text x="460" y="378" class="sb" text-anchor="middle">backups + artifacts</text>

  <!-- BackupFS -->
  <rect x="560" y="420" width="160" height="72" rx="6" fill="rgba(231,229,228,0.03)" stroke="rgba(231,229,228,0.30)" stroke-width="1"/>
  <rect x="568" y="428" width="44" height="12" rx="2" fill="transparent" stroke="rgba(231,229,228,0.30)" stroke-width="0.8"/>
  <text x="590" y="437" class="cp" fill="#a8a29e" text-anchor="middle">MOUNT</text>
  <text x="640" y="462" class="nm" text-anchor="middle">Backup files</text>
  <text x="640" y="478" class="sb" text-anchor="middle">Finder / iTunes</text>

  <line x1="40" y1="520" x2="1000" y2="520" stroke="rgba(231,229,228,0.10)" stroke-width="0.8"/>
  <text x="40" y="538" class="lb">SOLID = sync request</text>
  <text x="280" y="538" class="lba">AMBER = async job dispatch</text>
  <text x="600" y="538" class="lb">DASHED = on-demand file read</text>
</svg>
</div>

## The five services

The split follows one rule: anything slow or CPU-heavy goes to the worker, so the API stays responsive.

- **FastAPI backend.** Serves the REST API for discovery, decryption, unlocking, manifest browsing, and the per-artifact views. It owns the database connection and enqueues jobs.
- **RQ worker.** Pulls jobs off Redis and runs the long operations: decrypting a backup and parsing its SQLite artifacts into Postgres. It shares the backend's Docker image, so it has the same parsers and models.
- **PostgreSQL.** The system of record. Holds the backup registry, the normalized artifact tables, and the search index. Tests and local runs fall back to SQLite.
- **Redis.** The job queue (`default`) plus RQ's own job metadata and heartbeats. It does not store session tokens or decrypted data.
- **React frontend.** The investigator UI, built with Vite and served by nginx. It calls the backend with an API token and, once a backup is unlocked, a session token.

## How a backup moves through the system

Five flows cover everything the tool does, in the order you hit them:

1. **Discover.** `BackupRegistry` scans the configured backup directory, records each backup's metadata in Postgres, and serves the list at `GET /backups`.
2. **Decrypt.** Posting the passphrase enqueues a worker job. The worker unlocks the keybag and Manifest with `iphone-backup-decrypt`, extracts the artifact databases, and marks the backup `DECRYPTED`. The UI polls until it finishes.
3. **Index.** Once decrypted, a job parses each artifact database into normalized rows and populates the cross-artifact search index. The backup moves to `INDEXED`.
4. **Browse.** The frontend reads the per-artifact endpoints, the global search, and the timeline straight from Postgres. No backup payloads are touched.
5. **Download.** When you open an attachment or photo, the backend reads that one file from disk (or the decrypted store), streams it, and deletes any temporary copy afterward.

## What this buys you

The backend holds no durable state of its own: Postgres is for persistence, Redis is for coordination, and the backups stay on disk. You can restart the API without losing anything, and a heavy indexing run never freezes the UI. If a backup is large, you watch the status tick over while the worker does the work.
