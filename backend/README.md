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

Aggregate one sensor's readings into PostgreSQL time buckets:

~~~text
GET /api/v1/telemetry/aggregate?sensor_id=<uuid>&start=<ISO8601>&end=<ISO8601>&bucket=5m
~~~

`start` and `end` are required timezone-aware bounds with a maximum range of 31 days.
The query uses `[start, end)` semantics and supports `1m`, `5m`, `15m`, and `1h` buckets
aligned to absolute UTC clock boundaries. Only buckets containing readings are returned.

The Machine Detail frontend derives descriptive threshold analytics from those populated
aggregate buckets. A bucket exceeds its persisted sensor-type threshold only when its maximum is
strictly greater than the threshold. Counts therefore describe buckets, and the displayed reading
total describes readings represented by exceeding buckets; neither metric claims exact time or
exact individual readings above the threshold.

## Predictive-maintenance feature foundation

The backend exposes an on-demand, versioned descriptive feature vector for a machine:

```text
GET /api/v1/machines/<machine_id>/predictive-features?window=24h&end=<ISO8601>
```

Supported lookback windows are `1h`, `6h`, `24h`, and `7d`; the default is `24h`. The optional
timezone-aware `end` makes extraction reproducible, and every sensor uses the same `[start, end)`
UTC window. Version `v1` includes reading count, mean, minimum, maximum, population standard
deviation (`STDDEV_POP`), deterministic first/last values, change metrics, persisted-threshold
ratios and strict reading-level exceedance metrics, time span, and `NO_DATA`/`SPARSE`/`SUFFICIENT`
coverage status. Features are calculated on demand and are not stored in a feature table.

These descriptive features are preparation for later evaluation. They are not a trained-model
prediction and do not represent failure probability, remaining useful life, or a predicted
breakdown date.

## Deterministic maintenance health score

The backend can transform the versioned feature vector into an explainable, on-demand maintenance
health indicator:

```text
GET /api/v1/machines/<machine_id>/health-score?window=24h&end=<ISO8601>
```

The response identifies both `feature_version` and `scoring_version`. Scores range from 0 to 100,
where higher is healthier, and use `HEALTHY` (80–100), `WATCH` (60–<80), `ATTENTION` (0–<60), or
`INSUFFICIENT_DATA`. Separate `NONE`, `LOW`, `MEDIUM`, and `HIGH` confidence values describe data
coverage rather than machine health.

Scoring version `v1` starts at 100 and subtracts capped, visible penalties for threshold proximity,
mean level, exact reading-level exceedance fraction, absolute trend magnitude, and
threshold-normalized variability. A machine score blends 70% of the equal-weight sensor average
with 30% of the lowest sensor score. Deterministic reasons explain the material contributions.

This indicator is not machine learning, failure probability, remaining useful life, or a predicted
breakdown date. Scores are not persisted and are not recalculated through realtime events.

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
