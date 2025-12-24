# Apple Juicer

A full-stack web application for extracting and analyzing data from iOS (Finder/iTunes) backups. Built with FastAPI, React, PostgreSQL, and Redis.

## Features

- **Backup Discovery** - Automatically discover and index iOS backups
- **Decryption** - Decrypt encrypted backups with password prompts
- **Artifact Parsing** - Extract and browse WhatsApp, Messages, Photos, Notes, Calendar, and Contacts
- **Search & Filter** - Search through manifest files and artifacts
- **Modern UI** - Clean, responsive interface built with React and TailwindCSS
- **Docker Ready** - Deploy with a single command using Docker Compose

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

3. Run database migrations:
```bash
alembic upgrade head
```

4. Start the backend:
```bash
uvicorn api.main:app --reload
```

## Documentation

Full documentation is available at [https://giovi321.github.io/apple-juicer](https://giovi321.github.io/apple-juicer)

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
