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

## Historical telemetry

Query recent raw readings for one sensor with optional inclusive,
timezone-aware bounds:

~~~text
GET /api/v1/telemetry/readings?sensor_id=<uuid>&start=<ISO8601>&end=<ISO8601>&limit=500
~~~

The API selects the newest requested readings within the range, then
returns that bounded set oldest to newest. The default limit is 500 and
the maximum is 5000.

## Development SSE infrastructure

The backend exposes a process-local Server-Sent Events stream for development:

```text
GET /api/v1/events/stream
```

Open the stream in one terminal:

```bash
curl -N http://127.0.0.1:8000/api/v1/events/stream
```

Each connection first receives a `system.connected` event. Idle streams receive an SSE comment
heartbeat every 15 seconds.

Successful operational changes publish these compact invalidation
events after their database transactions commit:

- `telemetry.updated` when a sensor reading is ingested
- `alert.created` when a new alert is persisted
- `alert.updated` when an existing alert changes lifecycle state

Event payloads contain only the affected sensor, machine, or alert
identifiers and the current alert status where applicable. Clients
should reload the relevant REST resource after receiving an event;
the REST APIs remain the authoritative application state.

When the backend `ENVIRONMENT` is `development`, publish a controlled test event from another
terminal:

```bash
curl -X POST \
  http://127.0.0.1:8000/api/v1/events/test \
  -H "Content-Type: application/json" \
  -d '{"type":"system.test","data":{"message":"hello"}}'
```

The broadcaster is transient, in-memory, and local to one FastAPI process. It is suitable for
local development but does not provide delivery across multiple workers or application instances.
