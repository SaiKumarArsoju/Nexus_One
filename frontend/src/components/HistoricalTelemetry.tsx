import { useEffect, useMemo, useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import {
  getSensors,
  getTelemetryAggregates,
} from "../api/client";

import type {
  SensorDiscovery,
  TelemetryAggregateBucket,
  TelemetryAggregationBucket,
} from "../types/api";
import type { TooltipContentProps } from "recharts";

type HistoricalTelemetryProps = {
  machineId: string;
};

type HistoricalRangeKey = "1h" | "6h" | "24h" | "7d" | "30d";

type HistoricalRange = {
  key: HistoricalRangeKey;
  label: string;
  durationMs: number;
  bucket: TelemetryAggregationBucket;
};

type HistoricalChartDatum = TelemetryAggregateBucket & {
  timestamp: number;
};

const MINUTE_MS = 60_000;
const HOUR_MS = 60 * MINUTE_MS;
const DAY_MS = 24 * HOUR_MS;

const HISTORICAL_RANGES: readonly HistoricalRange[] = [
  { key: "1h", label: "Last 1 hour", durationMs: HOUR_MS, bucket: "1m" },
  { key: "6h", label: "Last 6 hours", durationMs: 6 * HOUR_MS, bucket: "5m" },
  { key: "24h", label: "Last 24 hours", durationMs: DAY_MS, bucket: "15m" },
  { key: "7d", label: "Last 7 days", durationMs: 7 * DAY_MS, bucket: "1h" },
  { key: "30d", label: "Last 30 days", durationMs: 30 * DAY_MS, bucket: "1h" },
];

const DEFAULT_RANGE_KEY: HistoricalRangeKey = "1h";
const NUMBER_FORMATTER = new Intl.NumberFormat(undefined, {
  maximumFractionDigits: 2,
});
const LOCAL_TIME_ZONE = Intl.DateTimeFormat().resolvedOptions().timeZone;

function requestErrorMessage(error: unknown): string {
  return error instanceof Error
    ? error.message
    : "An unexpected request error occurred.";
}

function formatValue(value: number, unit: string): string {
  return `${NUMBER_FORMATTER.format(value)} ${unit}`;
}

function formatLocalTimestamp(timestamp: number): string {
  return new Date(timestamp).toLocaleString([], {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function formatAxisTimestamp(timestamp: number, range: HistoricalRangeKey): string {
  const options: Intl.DateTimeFormatOptions =
    range === "1h" || range === "6h" || range === "24h"
      ? { hour: "2-digit", minute: "2-digit" }
      : { month: "short", day: "numeric", hour: "2-digit" };

  return new Date(timestamp).toLocaleString([], options);
}

function HistoricalTooltip({
  active,
  payload,
  unit,
}: TooltipContentProps & { unit: string }) {
  if (!active || !payload?.length) {
    return null;
  }

  const point = payload[0].payload as HistoricalChartDatum;

  return (
    <div className="historical-tooltip">
      <strong>{formatLocalTimestamp(point.timestamp)}</strong>
      <span>Average: {formatValue(point.average, unit)}</span>
      <span>Minimum: {formatValue(point.minimum, unit)}</span>
      <span>Maximum: {formatValue(point.maximum, unit)}</span>
      <span>Reading count: {point.count.toLocaleString()}</span>
    </div>
  );
}

function HistoricalTelemetry({ machineId }: HistoricalTelemetryProps) {
  const [sensors, setSensors] = useState<SensorDiscovery[]>([]);
  const [selectedSensorId, setSelectedSensorId] = useState("");
  const [rangeKey, setRangeKey] =
    useState<HistoricalRangeKey>(DEFAULT_RANGE_KEY);
  const [sensorRefreshVersion, setSensorRefreshVersion] = useState(0);
  const [refreshVersion, setRefreshVersion] = useState(0);
  const [sensorLoading, setSensorLoading] = useState(true);
  const [sensorError, setSensorError] = useState("");
  const [data, setData] = useState<TelemetryAggregateBucket[]>([]);
  const [dataLoading, setDataLoading] = useState(false);
  const [dataError, setDataError] = useState("");

  const selectedRange =
    HISTORICAL_RANGES.find((range) => range.key === rangeKey) ??
    HISTORICAL_RANGES[0];
  const selectedSensor = sensors.find(
    (sensor) => sensor.id === selectedSensorId,
  );
  const chartData = useMemo<HistoricalChartDatum[]>(
    () =>
      data.map((bucket) => ({
        ...bucket,
        timestamp: new Date(bucket.bucket_start).getTime(),
      })),
    [data],
  );

  useEffect(() => {
    const controller = new AbortController();
    let current = true;

    setSensors([]);
    setSelectedSensorId("");
    setSensorLoading(true);
    setSensorError("");
    setData([]);
    setDataError("");

    getSensors(controller.signal)
      .then((allSensors) => {
        if (!current) {
          return;
        }

        const machineSensors = allSensors
          .filter((sensor) => sensor.machine_id === machineId)
          .sort(
            (left, right) =>
              left.name.localeCompare(right.name) ||
              left.sensor_type.localeCompare(right.sensor_type) ||
              left.id.localeCompare(right.id),
          );

        setSensors(machineSensors);
        setSelectedSensorId(machineSensors[0]?.id ?? "");
      })
      .catch((error: unknown) => {
        if (current && !controller.signal.aborted) {
          setSensorError(requestErrorMessage(error));
        }
      })
      .finally(() => {
        if (current) {
          setSensorLoading(false);
        }
      });

    return () => {
      current = false;
      controller.abort();
    };
  }, [machineId, sensorRefreshVersion]);

  useEffect(() => {
    if (!selectedSensorId) {
      setData([]);
      setDataLoading(false);
      return;
    }

    const controller = new AbortController();
    let current = true;
    const end = new Date();
    const start = new Date(end.getTime() - selectedRange.durationMs);

    setData([]);
    setDataLoading(true);
    setDataError("");

    getTelemetryAggregates(
      {
        sensorId: selectedSensorId,
        start: start.toISOString(),
        end: end.toISOString(),
        bucket: selectedRange.bucket,
      },
      controller.signal,
    )
      .then((nextData) => {
        if (current) {
          setData(nextData);
        }
      })
      .catch((error: unknown) => {
        if (current && !controller.signal.aborted) {
          setDataError(requestErrorMessage(error));
        }
      })
      .finally(() => {
        if (current) {
          setDataLoading(false);
        }
      });

    return () => {
      current = false;
      controller.abort();
    };
  }, [refreshVersion, selectedRange, selectedSensorId]);

  return (
    <section className="section historical-telemetry">
      <div className="section-heading-row historical-heading">
        <div>
          <h2>Historical Telemetry</h2>
          <p>
            Aggregated readings shown in your local timezone ({LOCAL_TIME_ZONE}).
          </p>
        </div>

        <div className="historical-controls">
          <label>
            <span>Sensor</span>
            <select
              className="filter-select historical-select"
              value={selectedSensorId}
              disabled={sensorLoading || sensors.length === 0}
              onChange={(event) => setSelectedSensorId(event.target.value)}
            >
              {sensors.length === 0 && (
                <option value="">
                  {sensorLoading ? "Loading sensors..." : "No sensors available"}
                </option>
              )}
              {sensors.map((sensor) => (
                <option key={sensor.id} value={sensor.id}>
                  {sensor.name} — {sensor.sensor_type} ({sensor.unit})
                </option>
              ))}
            </select>
          </label>

          <label>
            <span>Time range</span>
            <select
              className="filter-select historical-select"
              value={rangeKey}
              disabled={!selectedSensorId}
              onChange={(event) =>
                setRangeKey(event.target.value as HistoricalRangeKey)
              }
            >
              {HISTORICAL_RANGES.map((range) => (
                <option key={range.key} value={range.key}>
                  {range.label}
                </option>
              ))}
            </select>
          </label>

          <button
            className="view-all-button historical-refresh"
            type="button"
            disabled={!selectedSensorId || dataLoading}
            onClick={() => setRefreshVersion((version) => version + 1)}
          >
            {dataLoading ? "Loading..." : "Refresh"}
          </button>
        </div>
      </div>

      {sensorError && (
        <div className="historical-state error" role="alert">
          <strong>Unable to load sensors.</strong>
          <span>{sensorError}</span>
          <button
            className="view-all-button"
            type="button"
            onClick={() =>
              setSensorRefreshVersion((version) => version + 1)
            }
          >
            Try again
          </button>
        </div>
      )}

      {!sensorError && sensorLoading && (
        <div className="historical-state" role="status">
          Loading sensors...
        </div>
      )}

      {!sensorError && !sensorLoading && sensors.length === 0 && (
        <div className="historical-state">
          No sensors are configured for this machine.
        </div>
      )}

      {!sensorError && selectedSensor && dataLoading && (
        <div className="historical-state" role="status">
          Loading historical telemetry...
        </div>
      )}

      {!sensorError && selectedSensor && !dataLoading && dataError && (
        <div className="historical-state error" role="alert">
          <strong>Unable to load historical telemetry.</strong>
          <span>{dataError}</span>
          <button
            className="view-all-button"
            type="button"
            onClick={() => setRefreshVersion((version) => version + 1)}
          >
            Try again
          </button>
        </div>
      )}

      {!sensorError &&
        selectedSensor &&
        !dataLoading &&
        !dataError &&
        chartData.length === 0 && (
          <div className="historical-state">
            No historical telemetry found for this sensor and time range.
          </div>
        )}

      {!sensorError &&
        selectedSensor &&
        !dataLoading &&
        !dataError &&
        chartData.length > 0 && (
          <article className="historical-chart-card">
            <div className="historical-chart-summary">
              <div>
                <strong>{selectedSensor.name}</strong>
                <span>
                  {selectedRange.label} · {selectedRange.bucket} buckets
                </span>
              </div>
              <span>{chartData.length.toLocaleString()} populated buckets</span>
            </div>

            <div className="historical-chart-container">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart
                  data={chartData}
                  margin={{ top: 10, right: 22, bottom: 8, left: 14 }}
                >
                  <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
                  <XAxis
                    dataKey="timestamp"
                    type="number"
                    domain={["dataMin", "dataMax"]}
                    scale="time"
                    tickFormatter={(timestamp: number) =>
                      formatAxisTimestamp(timestamp, rangeKey)
                    }
                    stroke="#64748b"
                    minTickGap={28}
                  />
                  <YAxis
                    stroke="#64748b"
                    tickFormatter={(value: number) =>
                      NUMBER_FORMATTER.format(value)
                    }
                    label={{
                      value: selectedSensor.unit,
                      angle: -90,
                      position: "insideLeft",
                      fill: "#94a3b8",
                    }}
                  />
                  <Tooltip
                    content={(tooltipProps) => (
                      <HistoricalTooltip
                        {...tooltipProps}
                        unit={selectedSensor.unit}
                      />
                    )}
                  />
                  <Legend />
                  <Line
                    type="linear"
                    dataKey="maximum"
                    name="Maximum"
                    stroke="#f59e0b"
                    strokeWidth={1.5}
                    strokeDasharray="5 4"
                    dot={false}
                  />
                  <Line
                    type="linear"
                    dataKey="average"
                    name="Average"
                    stroke="#60a5fa"
                    strokeWidth={3}
                    dot={false}
                  />
                  <Line
                    type="linear"
                    dataKey="minimum"
                    name="Minimum"
                    stroke="#22c55e"
                    strokeWidth={1.5}
                    strokeDasharray="5 4"
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </article>
        )}
    </section>
  );
}

export default HistoricalTelemetry;
