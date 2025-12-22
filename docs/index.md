# Apple Juicer

Apple Juicer is a full-stack web application that lets investigators, DFIR specialists, and power users extract and analyze data from iOS (Finder/iTunes) backups directly in the browser. It combines:

- **FastAPI backend** for backup discovery, decryption, and artifact browsing
- **Redis + RQ worker** for background indexing of artifacts
- **React + Vite frontend** with modern UI for exploring backups
- **PostgreSQL** as the system-of-record for backups and indexed artifacts

## Key Capabilities

1. **Backup Discovery** - Automatically discover iOS backups from configured directories
2. **Persistent Decryption** - Decrypt encrypted backups once and store decrypted data server-side
3. **Artifact Parsing** - Extract and index WhatsApp, Messages, Photos, Notes, Calendar, and Contacts
4. **Advanced Search** - Search through manifest files, chats, and messages with filtering
5. **Modern UI** - Responsive interface with lazy loading, search, and sorting capabilities
6. **Docker Deployment** - Deploy all services with a single Docker Compose command

## New Features (v0.1.0)

- **Persistent Decryption Workflow** - Decrypt once, explore without re-entering passwords
- **WhatsApp Module** - Browse chats with lazy loading (100 messages at a time), search, and sorting
- **Enhanced UI** - Improved navigation, backup metadata display, and scrollable containers
- **Delete Decrypted Data** - Safely remove decrypted data while keeping encrypted backups
- **Logging Configuration** - Configurable log levels and rotation with no sensitive data exposure

## High-Level Architecture

```
           ┌──────────────────────┐
           │   React Frontend     │
           │ (Vite + Nginx)       │
           └─────────┬────────────┘
                     │ HTTPS (X-API-Token)
┌────────────────────▼────────────────────┐
│             FastAPI Backend             │
│  • Backup discovery + registry          │
│  • Session + unlock management          │
│  • Manifest browsing/download           │
└─────┬───────────────────────────────┬───┘
      │ Postgres (async SQLAlchemy)   │
      │                               │ Redis (RQ)
┌─────▼──────────────┐         ┌──────▼───────────────┐
│ Backup Registry DB │         │  Worker + Parsers     │
│ backups, sessions  │         │  Queue “default”      │
└────────────────────┘         └──────────────────────┘
```

## Documentation Structure

- **Quickstart** – Run locally or with Docker Compose.
- **Architecture** – Detailed component breakdowns and data flows.
- **Operations** – Configuration, background tasks, and troubleshooting.
- **Reference** – API contract and repository layout.

Use the left navigation to jump into the section you need, or search from anywhere with `Cmd/Ctrl + K`.***
