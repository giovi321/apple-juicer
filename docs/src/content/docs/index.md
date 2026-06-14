---
title: "Apple Juicer"
description: "Self-hosted tool for extracting and analyzing data from iOS (Finder/iTunes) backups."
---

<div style="text-align: center; margin-bottom: 1rem;">
  <img src="assets/logo.svg" alt="Apple Juicer" width="96" height="96" style="border-radius: 12px;" />
</div>

**Turn an iOS backup into browsable forensic artifacts.**

Point Apple Juicer at a folder of Finder/iTunes backups. It discovers them, decrypts the encrypted ones in the background, indexes ten artifact types into a database, and gives you a web UI to browse conversations, photos, call history, locations and more, search across all of them at once, and export what you find.

:::danger[Personal-use software, not safe to expose to the public internet]
Apple Juicer is built for one investigator running it on their own machine, not as a hardened multi-user service. Run it on a **trusted LAN, a single-user workstation, or behind a VPN / authenticating reverse proxy** — never bound directly to a public IP.

Authentication is a single static API token with no rotation, rate limiting, or lockout. Decrypted backups are written to disk in plaintext. The unlock passphrase travels to the worker as a job argument. These are deliberate trade-offs for a local tool; the [Security](operations/security/) page lists every one of them and how to compensate if you need to.
:::

<div class="diagram-frame">
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 980 360" role="img" aria-label="Apple Juicer — drop in an encrypted backup, browse forensic artifacts out">
  <defs>
    <pattern id="dots-hero" width="22" height="22" patternUnits="userSpaceOnUse">
      <circle cx="1" cy="1" r="0.9" fill="rgba(231,229,228,0.06)"/>
    </pattern>
    <marker id="arrow-hero" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
      <polygon points="0 0, 8 3, 0 6" fill="#a8a29e"/>
    </marker>
    <marker id="arrow-hero-accent" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
      <polygon points="0 0, 8 3, 0 6" fill="#f59e0b"/>
    </marker>
    <style>
      .eyebrow{font-family:'Geist Mono','SF Mono',Menlo,monospace;font-size:9px;letter-spacing:0.2em;fill:#a8a29e;}
      .name{font-family:'Geist','Inter',system-ui,sans-serif;font-weight:600;font-size:13px;fill:#fafaf9;}
      .sub{font-family:'Geist Mono','SF Mono',Menlo,monospace;font-size:10px;fill:#a8a29e;}
      .label{font-family:'Geist Mono','SF Mono',Menlo,monospace;font-size:9px;fill:#a8a29e;letter-spacing:0.06em;}
      .label-accent{font-family:'Geist Mono','SF Mono',Menlo,monospace;font-size:9px;fill:#f59e0b;letter-spacing:0.06em;}
      .title{font-family:'Instrument Serif',Georgia,serif;font-size:22px;fill:#fafaf9;}
      .ital{font-family:'Instrument Serif',Georgia,serif;font-style:italic;font-size:13px;fill:#a8a29e;}
      .chip{font-family:'Geist Mono','SF Mono',Menlo,monospace;font-size:8px;letter-spacing:0.08em;}
    </style>
  </defs>
  <rect width="100%" height="100%" fill="#1c1917"/>
  <rect width="100%" height="100%" fill="url(#dots-hero)" opacity="0.6"/>
  <text x="40" y="44" class="eyebrow">APPLE JUICER · PIPELINE</text>
  <text x="40" y="76" class="title">Drop in an encrypted backup, browse forensic artifacts out</text>

  <line x1="208" y1="200" x2="268" y2="200" stroke="#a8a29e" stroke-width="1" marker-end="url(#arrow-hero)"/>
  <line x1="436" y1="200" x2="496" y2="200" stroke="#a8a29e" stroke-width="1" marker-end="url(#arrow-hero)"/>
  <line x1="664" y1="200" x2="724" y2="200" stroke="#f59e0b" stroke-width="1.2" marker-end="url(#arrow-hero-accent)"/>
  <rect x="210" y="184" width="56" height="12" rx="2" fill="#1c1917"/>
  <text x="238" y="193" class="label" text-anchor="middle">ENCRYPTED</text>
  <rect x="440" y="184" width="52" height="12" rx="2" fill="#1c1917"/>
  <text x="466" y="193" class="label" text-anchor="middle">MANIFEST</text>
  <rect x="668" y="184" width="52" height="12" rx="2" fill="#1c1917"/>
  <text x="694" y="193" class="label-accent" text-anchor="middle">ARTIFACTS</text>

  <rect x="40" y="140" width="168" height="120" rx="6" fill="rgba(231,229,228,0.04)" stroke="#78716c" stroke-width="1"/>
  <rect x="48" y="148" width="44" height="14" rx="2" fill="transparent" stroke="rgba(120,113,108,0.55)" stroke-width="0.8"/>
  <text x="70" y="158" class="chip" fill="#a8a29e" text-anchor="middle">SCAN</text>
  <text x="124" y="194" class="name" text-anchor="middle">Discover</text>
  <text x="124" y="214" class="sub" text-anchor="middle">backup paths</text>
  <text x="124" y="238" class="ital" text-anchor="middle">find backups on disk</text>

  <rect x="268" y="140" width="168" height="120" rx="6" fill="rgba(231,229,228,0.06)" stroke="#a8a29e" stroke-width="1"/>
  <rect x="276" y="148" width="52" height="14" rx="2" fill="transparent" stroke="rgba(168,162,158,0.55)" stroke-width="0.8"/>
  <text x="302" y="158" class="chip" fill="#a8a29e" text-anchor="middle">WORKER</text>
  <text x="352" y="194" class="name" text-anchor="middle">Decrypt</text>
  <text x="352" y="214" class="sub" text-anchor="middle">keybag + manifest</text>
  <text x="352" y="238" class="ital" text-anchor="middle">background job</text>

  <rect x="496" y="140" width="168" height="120" rx="6" fill="rgba(231,229,228,0.06)" stroke="#a8a29e" stroke-width="1"/>
  <rect x="504" y="148" width="52" height="14" rx="2" fill="transparent" stroke="rgba(168,162,158,0.55)" stroke-width="0.8"/>
  <text x="530" y="158" class="chip" fill="#a8a29e" text-anchor="middle">WORKER</text>
  <text x="580" y="194" class="name" text-anchor="middle">Index</text>
  <text x="580" y="214" class="sub" text-anchor="middle">registry ingest</text>
  <text x="580" y="238" class="ital" text-anchor="middle">parse SQLite → DB</text>

  <rect x="724" y="140" width="168" height="120" rx="6" fill="rgba(245,158,11,0.14)" stroke="#f59e0b" stroke-width="1.2"/>
  <rect x="732" y="148" width="32" height="14" rx="2" fill="transparent" stroke="rgba(245,158,11,0.55)" stroke-width="0.8"/>
  <text x="748" y="158" class="chip" fill="#f59e0b" text-anchor="middle">UI</text>
  <text x="808" y="194" class="name" text-anchor="middle">Browse</text>
  <text x="808" y="214" class="sub" text-anchor="middle">10 artifact types</text>
  <text x="808" y="238" class="ital" text-anchor="middle">search · timeline · export</text>

  <line x1="40" y1="304" x2="940" y2="304" stroke="rgba(231,229,228,0.10)" stroke-width="0.8"/>
  <text x="40" y="324" class="ital">Self-hosted. Your backups never leave your machine.</text>
  <text x="940" y="324" class="label" text-anchor="end">github.com/giovi321/apple-juicer</text>
</svg>
</div>

## What it pulls out of a backup

Apple Juicer indexes ten artifact types, each with its own browsable view:

| Artifact | Source | What you get |
|----------|--------|--------------|
| WhatsApp | `ChatStorage.sqlite` | Chats, messages, attachments |
| Messages | `chat.db` | iMessage and SMS conversations |
| Photos | `Photos.sqlite` | Photo timeline with thumbnails and full-size view |
| Notes | `NoteStore.sqlite` | Note bodies and folders |
| Calendar | `Calendar.sqlitedb` | Events and calendars |
| Contacts | `AddressBook.sqlitedb` | Address book entries |
| Calls | `CallHistory.storedata` | Call log |
| Safari | `History.db` | Browsing history |
| Locations | `routined` caches | Significant locations |
| Voicemail | `voicemail.db` | Voicemail messages |

On top of the per-artifact views, four features cut across all of them:

- **People.** A contact-centric view that collapses one person's WhatsApp messages, iMessages, calls, and voicemails into a single entity, with the name resolved from Contacts. It answers *who*, where search answers *what* and the timeline answers *when*.
- **Global search.** One query runs against every indexed type, and a hit links straight back to the conversation or record it came from.
- **Unified timeline.** Messages, photos, calls and the rest merge into a single reverse-chronological stream.
- **Export.** Download any tabular view as CSV, or generate a one-page PDF summary of the whole backup.

## Quick start

```bash
git clone https://github.com/giovi321/apple-juicer.git
cd apple-juicer
docker compose up -d
```

Open [http://localhost:5173](http://localhost:5173), paste the API token (`dev-token` by default), and refresh to discover the backups under your mounted directory. See [Quick Start](getting-started/quickstart/) for the full walkthrough.

## How it fits together

Apple Juicer runs as five services behind Docker Compose: a FastAPI backend, an RQ worker for the slow parsing jobs, PostgreSQL for the indexed data, Redis for the job queue, and a React frontend served by nginx. The backend stays responsive while the worker chews through a backup in the background, and the original backups stay on disk, mounted read-only.

See the [Architecture Overview](architecture/overview/) for the full picture.

## Tech stack

| Component | Technology |
|-----------|-----------|
| Backend | Python 3.12 + FastAPI + async SQLAlchemy |
| Worker | RQ (Redis Queue) |
| Frontend | React 19 + TypeScript + Vite 7 |
| Database | PostgreSQL 16 (SQLite for tests and local runs) |
| Queue | Redis 7 |
| Decryption | iphone-backup-decrypt |
| Deployment | Docker Compose |
