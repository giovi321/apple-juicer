<p align="center">
  <img src="docs/src/assets/logo.svg" alt="Apple Juicer" width="120" />
</p>

<h1 align="center">Apple Juicer</h1>

<p align="center">
  <a href="https://github.com/giovi321/apple-juicer/actions/workflows/ci.yml"><img src="https://github.com/giovi321/apple-juicer/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://github.com/giovi321/apple-juicer/actions/workflows/docs.yml"><img src="https://github.com/giovi321/apple-juicer/actions/workflows/docs.yml/badge.svg" alt="Docs"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-GPLv3-blue.svg" alt="License: GPLv3"></a>
  <img src="https://img.shields.io/badge/python-3.11%2B-blue" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/node-20%2B-green" alt="Node 20+">
</p>

<p align="center">
  <a href="https://giovi321.github.io/apple-juicer/"><img src="https://img.shields.io/badge/Read_the_docs-2563eb?style=for-the-badge&logo=readthedocs&logoColor=white" alt="Read the documentation"></a>
</p>

A full-stack web application for extracting and analyzing data from iOS (Finder/iTunes) backups. Built with FastAPI, React, PostgreSQL, and Redis.

## Features

- **Backup Discovery** - Automatically discover and index iOS backups
- **Decryption** - Decrypt encrypted backups in the background (the UI stays responsive and polls for completion)
- **Artifact Parsing** - Extract and browse WhatsApp, Messages (iMessage/SMS), Photos, Notes, Calendar, Contacts, Call history, Safari history, Significant Locations, and Voicemail
- **Photo viewer** - View and download the actual images, not just metadata
- **Unified timeline** - A cross-artifact chronological view that merges messages, photos, calls and more into one stream
- **Global search** - Search across every indexed artifact type at once, with deep links into the originating conversation
- **CSV export** - Export the tabular artifact views (Photos, Notes, Calendar, Contacts, Calls, Safari, Locations, Voicemail) to CSV
- **PDF report** - Generate a per-backup summary report
- **Modern UI** - Clean, responsive interface built with React and Vite
- **Docker Ready** - Deploy with a single command using Docker Compose

New artifact types are a single registration in `core/artifacts/registry.py` (parser + spec + schema + router + UI tab).

## Quick Start

### Using Docker Compose (Recommended)

1. Clone the repository:
```bash
git clone https://github.com/giovi321/apple-juicer.git
cd apple-juicer
```

2. Configure environment (optional):
```bash
cp .env.example .env
# Edit .env with your settings
```

3. Start all services:
```bash
docker compose up -d
```

4. Access the application:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8080
- Default API token: `dev-token`

### Local Development

1. Set up Python environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

2. Set up frontend:
```bash
cd frontend
npm install
npm run dev
```

3. Run database migrations (optional — the backend also applies them automatically on startup):
```bash
alembic upgrade head
```

4. Start the backend:
```bash
uvicorn api.main:create_app --factory --reload
```

## Architecture

- **Backend**: FastAPI with async SQLAlchemy
- **Worker**: RQ (Redis Queue) for background tasks
- **Frontend**: React + Vite + TypeScript
- **Database**: PostgreSQL 16
- **Cache**: Redis 7

## Configuration

See `.env.example` for all available configuration options. Key settings:

- `APPLE_JUICER_BACKUP_HOST_PATH` - Path to your iOS backups directory
- `APPLE_JUICER_API_TOKEN` - API authentication token
- `LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR)

## Security

- All sensitive data (passwords, message content) is never logged
- API requires authentication token
- Encrypted backups are decrypted server-side and stored securely
- Docker containers use minimal privileges

## License

GNU General Public License v3.0 – see LICENSE for details

## Contributing

Contributions are welcome! Please read the documentation for development guidelines.
