from __future__ import annotations

import argparse
import math
import random
import sys
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

import httpx

DEFAULT_API_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_INTERVAL = 1.0
DEFAULT_CYCLES = 0
REQUEST_TIMEOUT_SECONDS = 10.0
MINIMUM_ABNORMAL_CYCLES = 3
MAXIMUM_ABNORMAL_CYCLES = 5


class SimulatorError(RuntimeError):
    pass


class SensorType(StrEnum):
    TEMPERATURE = "TEMPERATURE"
    PRESSURE = "PRESSURE"
    VIBRATION = "VIBRATION"
    RPM = "RPM"
    ENERGY = "ENERGY"


class SimulationPhase(StrEnum):
    NORMAL = "NORMAL"
    ABNORMAL = "ABNORMAL"
    RECOVERY = "RECOVERY"


@dataclass(frozen=True)
class SensorInfo:
    id: str
    name: str
    sensor_type: SensorType
    unit: str
    machine_id: str


@dataclass(frozen=True)
class SensorProfile:
    baseline_ratio: float
    normal_min_ratio: float
    normal_max_ratio: float
    drift_ratio: float
    abnormal_min_ratio: float
    abnormal_max_ratio: float
    recovery_step_ratio: float
    episode_chance: float
    display_precision: int


@dataclass
class SensorState:
    sensor: SensorInfo
    value: float
    phase: SimulationPhase = SimulationPhase.NORMAL
    abnormal_cycles_remaining: int = 0


@dataclass(frozen=True)
class SimulationConfig:
    api_base_url: str
    interval: float
    cycles: int
    seed: int | None

    @property
    def continuous(self) -> bool:
        return self.cycles == 0


@dataclass(frozen=True)
class IngestionResult:
    status_code: int | None
    error: str | None = None

    @property
    def successful(self) -> bool:
        return self.status_code == httpx.codes.CREATED and self.error is None


@dataclass(frozen=True)
class RunSummary:
    cycles_completed: int
    attempted: int
    succeeded: int
    failed: int


SENSOR_PROFILES: dict[SensorType, SensorProfile] = {
    SensorType.TEMPERATURE: SensorProfile(
        baseline_ratio=0.72,
        normal_min_ratio=0.58,
        normal_max_ratio=0.86,
        drift_ratio=0.012,
        abnormal_min_ratio=1.03,
        abnormal_max_ratio=1.12,
        recovery_step_ratio=0.08,
        episode_chance=0.04,
        display_precision=2,
    ),
    SensorType.PRESSURE: SensorProfile(
        baseline_ratio=0.70,
        normal_min_ratio=0.60,
        normal_max_ratio=0.88,
        drift_ratio=0.007,
        abnormal_min_ratio=1.02,
        abnormal_max_ratio=1.08,
        recovery_step_ratio=0.07,
        episode_chance=0.03,
        display_precision=2,
    ),
    SensorType.VIBRATION: SensorProfile(
        baseline_ratio=0.35,
        normal_min_ratio=0.15,
        normal_max_ratio=0.65,
        drift_ratio=0.02,
        abnormal_min_ratio=1.08,
        abnormal_max_ratio=1.30,
        recovery_step_ratio=0.12,
        episode_chance=0.035,
        display_precision=3,
    ),
    SensorType.RPM: SensorProfile(
        baseline_ratio=0.75,
        normal_min_ratio=0.55,
        normal_max_ratio=0.90,
        drift_ratio=0.02,
        abnormal_min_ratio=1.02,
        abnormal_max_ratio=1.09,
        recovery_step_ratio=0.09,
        episode_chance=0.025,
        display_precision=0,
    ),
    SensorType.ENERGY: SensorProfile(
        baseline_ratio=0.68,
        normal_min_ratio=0.45,
        normal_max_ratio=0.88,
        drift_ratio=0.018,
        abnormal_min_ratio=1.03,
        abnormal_max_ratio=1.14,
        recovery_step_ratio=0.09,
        episode_chance=0.03,
        display_precision=2,
    ),
}


def positive_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed) or parsed <= 0:
        raise argparse.ArgumentTypeError("must be a finite number greater than 0")
    return parsed


def nonnegative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be greater than or equal to 0")
    return parsed


def parse_args(argv: Sequence[str] | None = None) -> SimulationConfig:
    parser = argparse.ArgumentParser(
        description="Generate development telemetry through the NEXUS ONE public API.",
    )
    parser.add_argument(
        "--api-base-url",
        default=DEFAULT_API_BASE_URL,
        help=f"Backend base URL (default: {DEFAULT_API_BASE_URL})",
    )
    parser.add_argument(
        "--interval",
        type=positive_float,
        default=DEFAULT_INTERVAL,
        help=f"Seconds between cycles; must be greater than 0 (default: {DEFAULT_INTERVAL})",
    )
    parser.add_argument(
        "--cycles",
        type=nonnegative_int,
        default=DEFAULT_CYCLES,
        help="Cycles to run; 0 runs continuously (default: 0)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Optional random seed for reproducible telemetry",
    )
    args = parser.parse_args(argv)

    return SimulationConfig(
        api_base_url=args.api_base_url.rstrip("/"),
        interval=args.interval,
        cycles=args.cycles,
        seed=args.seed,
    )


def _response_error(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        payload = None

    if isinstance(payload, dict) and isinstance(payload.get("detail"), str):
        return payload["detail"]

    text = response.text.strip()
    return text[:200] if text else response.reason_phrase


def _get_json_list(
    client: httpx.Client,
    url: str,
    *,
    operation: str,
) -> list[object]:
    try:
        response = client.get(url)
    except httpx.RequestError as exc:
        raise SimulatorError(f"{operation} failed: {exc}") from exc

    if response.status_code != httpx.codes.OK:
        raise SimulatorError(
            f"{operation} failed: HTTP {response.status_code}: {_response_error(response)}"
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise SimulatorError(f"{operation} failed: response was not valid JSON") from exc

    if not isinstance(payload, list):
        raise SimulatorError(f"{operation} failed: expected a JSON array")

    return payload


def discover_sensors(client: httpx.Client, api_base_url: str) -> list[SensorInfo]:
    payload = _get_json_list(
        client,
        f"{api_base_url}/api/v1/sensors",
        operation="Sensor discovery",
    )
    sensors: list[SensorInfo] = []

    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise SimulatorError(f"Sensor discovery failed: item {index} is not an object")

        try:
            sensor_id = str(UUID(str(item["id"])))
            machine_id = str(UUID(str(item["machine_id"])))
            sensor_type = SensorType(item["sensor_type"])
            name = item["name"]
            unit = item["unit"]
        except (KeyError, TypeError, ValueError) as exc:
            raise SimulatorError(f"Sensor discovery failed: malformed item {index}") from exc

        if not isinstance(name, str) or not name or not isinstance(unit, str) or not unit:
            raise SimulatorError(f"Sensor discovery failed: malformed item {index}")

        sensors.append(
            SensorInfo(
                id=sensor_id,
                name=name,
                sensor_type=sensor_type,
                unit=unit,
                machine_id=machine_id,
            )
        )

    return sensors


def discover_thresholds(
    client: httpx.Client,
    api_base_url: str,
) -> dict[SensorType, float]:
    payload = _get_json_list(
        client,
        f"{api_base_url}/api/v1/alert-thresholds",
        operation="Threshold discovery",
    )
    thresholds: dict[SensorType, float] = {}

    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise SimulatorError(f"Threshold discovery failed: item {index} is not an object")

        try:
            sensor_type = SensorType(item["sensor_type"])
            threshold = float(item["threshold_value"])
        except (KeyError, TypeError, ValueError) as exc:
            raise SimulatorError(f"Threshold discovery failed: malformed item {index}") from exc

        if sensor_type in thresholds:
            raise SimulatorError(
                f"Threshold discovery failed: duplicate threshold for {sensor_type.value}"
            )
        if not math.isfinite(threshold) or threshold <= 0:
            raise SimulatorError(
                f"Threshold discovery failed: invalid threshold for {sensor_type.value}"
            )

        thresholds[sensor_type] = threshold

    missing = [sensor_type.value for sensor_type in SensorType if sensor_type not in thresholds]
    if missing:
        raise SimulatorError(
            f"Threshold discovery failed: missing thresholds for {', '.join(missing)}"
        )

    return thresholds


def initialize_sensor_state(
    sensor: SensorInfo,
    threshold: float,
    rng: random.Random,
) -> SensorState:
    profile = SENSOR_PROFILES[sensor.sensor_type]
    initial_ratio = profile.baseline_ratio + rng.uniform(
        -profile.drift_ratio,
        profile.drift_ratio,
    )
    return SensorState(sensor=sensor, value=threshold * initial_ratio)


def initialize_sensor_states(
    sensors: Sequence[SensorInfo],
    thresholds: dict[SensorType, float],
    rng: random.Random,
) -> dict[str, SensorState]:
    return {
        sensor.id: initialize_sensor_state(sensor, thresholds[sensor.sensor_type], rng)
        for sensor in sensors
    }


def generate_value(
    state: SensorState,
    threshold: float,
    rng: random.Random,
) -> float:
    profile = SENSOR_PROFILES[state.sensor.sensor_type]

    if state.phase == SimulationPhase.NORMAL and rng.random() < profile.episode_chance:
        state.phase = SimulationPhase.ABNORMAL
        state.abnormal_cycles_remaining = rng.randint(
            MINIMUM_ABNORMAL_CYCLES,
            MAXIMUM_ABNORMAL_CYCLES,
        )

    if state.phase == SimulationPhase.NORMAL:
        state.value += threshold * rng.uniform(
            -profile.drift_ratio,
            profile.drift_ratio,
        )
        state.value = min(
            max(state.value, threshold * profile.normal_min_ratio),
            threshold * profile.normal_max_ratio,
        )
    elif state.phase == SimulationPhase.ABNORMAL:
        abnormal_target = threshold * rng.uniform(
            profile.abnormal_min_ratio,
            profile.abnormal_max_ratio,
        )
        state.value += (abnormal_target - state.value) * 0.65
        state.value = max(state.value, threshold * profile.abnormal_min_ratio)
        state.abnormal_cycles_remaining -= 1

        if state.abnormal_cycles_remaining <= 0:
            state.phase = SimulationPhase.RECOVERY
            state.abnormal_cycles_remaining = 0
    else:
        normal_target = threshold * profile.baseline_ratio
        recovery_step = max(
            (state.value - normal_target) * 0.45,
            threshold * profile.recovery_step_ratio,
        )
        state.value = max(normal_target, state.value - recovery_step)

        if state.value <= threshold * profile.normal_max_ratio:
            state.phase = SimulationPhase.NORMAL

    if not math.isfinite(state.value):
        raise SimulatorError(f"Generated a non-finite value for sensor {state.sensor.name}")

    return state.value


def post_reading(
    client: httpx.Client,
    api_base_url: str,
    sensor: SensorInfo,
    value: float,
    recorded_at: datetime,
) -> IngestionResult:
    timestamp = recorded_at.astimezone(UTC).isoformat().replace("+00:00", "Z")
    try:
        response = client.post(
            f"{api_base_url}/api/v1/telemetry/readings",
            json={
                "sensor_id": sensor.id,
                "value": value,
                "recorded_at": timestamp,
            },
        )
    except httpx.RequestError as exc:
        return IngestionResult(status_code=None, error=str(exc))

    if response.status_code != httpx.codes.CREATED:
        return IngestionResult(
            status_code=response.status_code,
            error=_response_error(response),
        )

    return IngestionResult(status_code=response.status_code)


def run_simulation(
    *,
    client: httpx.Client,
    config: SimulationConfig,
    sensors: Sequence[SensorInfo],
    thresholds: dict[SensorType, float],
    rng: random.Random,
    sleep_fn: Callable[[float], None] = time.sleep,
    now_fn: Callable[[], datetime] = lambda: datetime.now(UTC),
    print_fn: Callable[[str], None] = print,
) -> RunSummary:
    states = initialize_sensor_states(sensors, thresholds, rng)
    cycle = 1
    attempted = 0
    succeeded = 0
    failed = 0

    while config.continuous or cycle <= config.cycles:
        for sensor in sensors:
            value = generate_value(
                states[sensor.id],
                thresholds[sensor.sensor_type],
                rng,
            )
            result = post_reading(
                client,
                config.api_base_url,
                sensor,
                value,
                now_fn(),
            )
            attempted += 1
            profile = SENSOR_PROFILES[sensor.sensor_type]
            rendered_value = f"{value:.{profile.display_precision}f}"

            if result.successful:
                succeeded += 1
                print_fn(
                    f"[cycle {cycle}] {sensor.name} | {sensor.sensor_type.value} | "
                    f"{rendered_value} {sensor.unit} | {result.status_code}"
                )
            else:
                failed += 1
                status = result.status_code if result.status_code is not None else "network error"
                print_fn(
                    f"[cycle {cycle}] {sensor.name} | {sensor.sensor_type.value} | "
                    f"{status} | {result.error}"
                )

        should_continue = config.continuous or cycle < config.cycles
        if should_continue:
            sleep_fn(config.interval)
        cycle += 1

    return RunSummary(
        cycles_completed=cycle - 1,
        attempted=attempted,
        succeeded=succeeded,
        failed=failed,
    )


def run_from_config(
    client: httpx.Client,
    config: SimulationConfig,
    *,
    sleep_fn: Callable[[float], None] = time.sleep,
    now_fn: Callable[[], datetime] = lambda: datetime.now(UTC),
    print_fn: Callable[[str], None] = print,
) -> RunSummary | None:
    sensors = discover_sensors(client, config.api_base_url)
    print_fn(f"[NEXUS] discovered {len(sensors)} sensors")

    if not sensors:
        print_fn("[NEXUS] no sensors found; nothing to simulate")
        return None

    thresholds = discover_thresholds(client, config.api_base_url)
    summary = run_simulation(
        client=client,
        config=config,
        sensors=sensors,
        thresholds=thresholds,
        rng=random.Random(config.seed),
        sleep_fn=sleep_fn,
        now_fn=now_fn,
        print_fn=print_fn,
    )
    print_fn(
        f"[NEXUS] completed {summary.cycles_completed} cycles | "
        f"{summary.succeeded} succeeded | {summary.failed} failed"
    )
    return summary


def main(argv: Sequence[str] | None = None) -> int:
    config = parse_args(argv)

    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS) as client:
            summary = run_from_config(client, config)
    except KeyboardInterrupt:
        print("\nNEXUS telemetry simulator stopped.")
        return 0
    except SimulatorError as exc:
        print(f"[NEXUS] error: {exc}", file=sys.stderr)
        return 1

    return 1 if summary is not None and summary.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
