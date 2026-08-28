import json
import math
import random
from datetime import UTC, datetime
from uuid import UUID

import httpx
import pytest

from scripts import generate_telemetry as simulator

API_BASE_URL = "http://testserver"
MACHINE_ID = "11111111-1111-1111-1111-111111111111"


def _sensor(
    sensor_type: simulator.SensorType = simulator.SensorType.TEMPERATURE,
    *,
    index: int = 1,
) -> simulator.SensorInfo:
    return simulator.SensorInfo(
        id=f"00000000-0000-0000-0000-{index:012d}",
        name=f"{sensor_type.value.title()} Sensor {index}",
        sensor_type=sensor_type,
        unit={
            simulator.SensorType.TEMPERATURE: "C",
            simulator.SensorType.PRESSURE: "bar",
            simulator.SensorType.VIBRATION: "mm/s",
            simulator.SensorType.RPM: "rpm",
            simulator.SensorType.ENERGY: "kWh",
        }[sensor_type],
        machine_id=MACHINE_ID,
    )


def _sensor_payload(
    sensor_type: simulator.SensorType = simulator.SensorType.TEMPERATURE,
    *,
    index: int = 1,
) -> dict[str, object]:
    sensor = _sensor(sensor_type, index=index)
    return {
        "id": sensor.id,
        "name": sensor.name,
        "sensor_type": sensor.sensor_type.value,
        "unit": sensor.unit,
        "machine_id": sensor.machine_id,
    }


def _thresholds(scale: float = 1.0) -> dict[simulator.SensorType, float]:
    return {
        sensor_type: scale * (index + 1) for index, sensor_type in enumerate(simulator.SensorType)
    }


def _threshold_payload(
    thresholds: dict[simulator.SensorType, float] | None = None,
) -> list[dict[str, object]]:
    values = thresholds or _thresholds()
    return [
        {
            "sensor_type": sensor_type.value,
            "threshold_value": threshold,
        }
        for sensor_type, threshold in values.items()
    ]


def _config(*, cycles: int = 1, interval: float = 0.25) -> simulator.SimulationConfig:
    return simulator.SimulationConfig(
        api_base_url=API_BASE_URL,
        interval=interval,
        cycles=cycles,
        seed=42,
    )


def _generated_sequence(seed: int) -> list[float]:
    sensor = _sensor()
    threshold = 90.0
    rng = random.Random(seed)
    state = simulator.initialize_sensor_state(sensor, threshold, rng)
    return [simulator.generate_value(state, threshold, rng) for _ in range(30)]


def test_fixed_seed_produces_deterministic_sequence():
    assert _generated_sequence(42) == _generated_sequence(42)
    assert _generated_sequence(42) != _generated_sequence(43)


def test_every_sensor_type_generates_finite_values():
    thresholds = _thresholds(10.0)

    for index, sensor_type in enumerate(simulator.SensorType, start=1):
        rng = random.Random(index)
        state = simulator.initialize_sensor_state(
            _sensor(sensor_type, index=index),
            thresholds[sensor_type],
            rng,
        )

        assert all(
            math.isfinite(simulator.generate_value(state, thresholds[sensor_type], rng))
            for _ in range(100)
        )


def test_each_sensor_maintains_independent_state():
    first = simulator.SensorState(
        sensor=_sensor(index=1),
        value=100.0,
        phase=simulator.SimulationPhase.ABNORMAL,
        abnormal_cycles_remaining=3,
    )
    second = simulator.SensorState(
        sensor=_sensor(index=2),
        value=65.0,
    )
    second_snapshot = (
        second.value,
        second.phase,
        second.abnormal_cycles_remaining,
    )

    simulator.generate_value(first, 90.0, random.Random(1))

    assert (
        second.value,
        second.phase,
        second.abnormal_cycles_remaining,
    ) == second_snapshot


def test_abnormal_episode_persists_for_multiple_cycles():
    threshold = 90.0
    state = simulator.SensorState(
        sensor=_sensor(),
        value=threshold * 1.05,
        phase=simulator.SimulationPhase.ABNORMAL,
        abnormal_cycles_remaining=simulator.MINIMUM_ABNORMAL_CYCLES,
    )
    rng = random.Random(42)

    values = [
        simulator.generate_value(state, threshold, rng)
        for _ in range(simulator.MINIMUM_ABNORMAL_CYCLES)
    ]

    assert all(value > threshold for value in values)
    assert state.phase == simulator.SimulationPhase.RECOVERY


def test_recovery_eventually_returns_to_normal_operation():
    threshold = 90.0
    state = simulator.SensorState(
        sensor=_sensor(),
        value=threshold * 1.20,
        phase=simulator.SimulationPhase.RECOVERY,
    )
    rng = random.Random(42)

    for _ in range(20):
        value = simulator.generate_value(state, threshold, rng)
        if state.phase == simulator.SimulationPhase.NORMAL:
            break

    assert state.phase == simulator.SimulationPhase.NORMAL
    assert value <= threshold


def test_changed_threshold_scales_generated_range():
    sensor = _sensor()
    first_rng = random.Random(42)
    second_rng = random.Random(42)
    first_state = simulator.initialize_sensor_state(sensor, 50.0, first_rng)
    second_state = simulator.initialize_sensor_state(sensor, 100.0, second_rng)

    first_values = [simulator.generate_value(first_state, 50.0, first_rng) for _ in range(10)]
    second_values = [simulator.generate_value(second_state, 100.0, second_rng) for _ in range(10)]

    assert second_values == pytest.approx([value * 2 for value in first_values])


def test_missing_threshold_configuration_fails_without_fallback():
    payload = _threshold_payload()
    payload.pop()

    with httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    ) as client:
        with pytest.raises(simulator.SimulatorError, match="missing thresholds for ENERGY"):
            simulator.discover_thresholds(client, API_BASE_URL)


def test_malformed_threshold_configuration_fails_clearly():
    payload = _threshold_payload()
    payload[0]["threshold_value"] = -1

    with httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    ) as client:
        with pytest.raises(simulator.SimulatorError, match="invalid threshold for TEMPERATURE"):
            simulator.discover_thresholds(client, API_BASE_URL)


def test_sensor_discovery_api_failure_fails_clearly():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"detail": "service unavailable"})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(
            simulator.SimulatorError,
            match="Sensor discovery failed: HTTP 503: service unavailable",
        ):
            simulator.discover_sensors(client, API_BASE_URL)


def test_threshold_discovery_api_failure_fails_clearly():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"detail": "threshold configuration unavailable"})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(
            simulator.SimulatorError,
            match="Threshold discovery failed: HTTP 500",
        ):
            simulator.discover_thresholds(client, API_BASE_URL)


def test_zero_discovered_sensors_exits_cleanly_without_threshold_request():
    requested_paths: list[str] = []
    output: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_paths.append(request.url.path)
        return httpx.Response(200, json=[])

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        summary = simulator.run_from_config(
            client,
            _config(),
            print_fn=output.append,
        )

    assert summary is None
    assert requested_paths == ["/api/v1/sensors"]
    assert output == [
        "[NEXUS] discovered 0 sensors",
        "[NEXUS] no sensors found; nothing to simulate",
    ]


def test_successful_post_uses_public_endpoint_and_valid_utc_payload():
    captured_request: httpx.Request | None = None
    sensor = _sensor()

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_request
        captured_request = request
        return httpx.Response(201, json={"id": str(UUID(int=99))})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = simulator.post_reading(
            client,
            API_BASE_URL,
            sensor,
            72.5,
            datetime(2026, 8, 28, 1, 30, tzinfo=UTC),
        )

    assert result.successful
    assert result.status_code == 201
    assert captured_request is not None
    assert captured_request.method == "POST"
    assert captured_request.url.path == "/api/v1/telemetry/readings"

    payload = json.loads(captured_request.content)
    recorded_at = datetime.fromisoformat(payload["recorded_at"].replace("Z", "+00:00"))

    assert set(payload) == {"sensor_id", "value", "recorded_at"}
    assert payload["sensor_id"] == sensor.id
    assert math.isfinite(payload["value"])
    assert recorded_at.tzinfo is not None
    assert recorded_at.utcoffset() == UTC.utcoffset(recorded_at)
    assert payload["recorded_at"].endswith("Z")


def test_failed_post_is_reported_and_remaining_sensors_continue():
    sensors = [_sensor(index=1), _sensor(index=2)]
    requests: list[httpx.Request] = []
    output: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if len(requests) == 1:
            return httpx.Response(500, json={"detail": "ingestion failed"})
        return httpx.Response(201, json={})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        summary = simulator.run_simulation(
            client=client,
            config=_config(),
            sensors=sensors,
            thresholds=_thresholds(90.0),
            rng=random.Random(42),
            sleep_fn=lambda interval: None,
            print_fn=output.append,
        )

    assert len(requests) == 2
    assert summary.attempted == 2
    assert summary.succeeded == 1
    assert summary.failed == 1
    assert any("500 | ingestion failed" in line for line in output)


@pytest.mark.parametrize("interval", ["0", "-1", "nan", "inf"])
def test_nonpositive_or_nonfinite_interval_is_rejected(interval):
    with pytest.raises(SystemExit):
        simulator.parse_args(["--interval", interval])


def test_negative_cycles_is_rejected():
    with pytest.raises(SystemExit):
        simulator.parse_args(["--cycles", "-1"])


def test_zero_cycles_represents_continuous_mode():
    config = simulator.parse_args(["--cycles", "0"])

    assert config.continuous


def test_finite_cycles_run_exact_count_and_do_not_sleep_after_last_cycle():
    sensors = [_sensor(index=1), _sensor(simulator.SensorType.PRESSURE, index=2)]
    requests: list[httpx.Request] = []
    sleeps: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(201, json={})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        summary = simulator.run_simulation(
            client=client,
            config=_config(cycles=3, interval=0.5),
            sensors=sensors,
            thresholds=_thresholds(90.0),
            rng=random.Random(42),
            sleep_fn=sleeps.append,
            print_fn=lambda message: None,
        )

    assert summary.cycles_completed == 3
    assert summary.attempted == 6
    assert len(requests) == 6
    assert sleeps == [0.5, 0.5]


def test_ctrl_c_shutdown_is_clean(monkeypatch, capsys):
    def interrupt(*args, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(simulator, "run_from_config", interrupt)

    exit_code = simulator.main(["--cycles", "0"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "NEXUS telemetry simulator stopped." in captured.out
    assert "Traceback" not in captured.out
    assert "Traceback" not in captured.err
