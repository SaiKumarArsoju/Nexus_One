# NEXUS ONE backend development

## Development telemetry simulator

The telemetry simulator is an explicitly started development process. It discovers the current
sensor inventory through `GET /api/v1/sensors`, reads persisted configuration through
`GET /api/v1/alert-thresholds`, and sends every generated value through
`POST /api/v1/telemetry/readings`. The backend remains responsible for threshold comparison and
the complete alert lifecycle.

Start PostgreSQL from the repository root and run the backend normally:

```bash
docker compose up -d postgres

cd backend
source .venv/bin/activate
alembic upgrade head
uvicorn app.main:app --reload
```

In a separate terminal, activate the backend environment and start a finite simulation:

```bash
cd backend
source .venv/bin/activate
python scripts/generate_telemetry.py --interval 1 --cycles 10 --seed 42
```

Use `--cycles 0` for continuous operation:

```bash
python scripts/generate_telemetry.py --interval 1 --cycles 0
```

The default API base URL is `http://127.0.0.1:8000`; override it with `--api-base-url` when
needed. Continuous mode runs until Ctrl+C and shuts down without a traceback.

This script is development tooling. It is not started by FastAPI or Docker Compose and does not
access PostgreSQL directly.
