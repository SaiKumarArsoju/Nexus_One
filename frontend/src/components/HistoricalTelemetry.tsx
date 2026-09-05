import { useEffect, useMemo, useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { getSensors, getTelemetryAggregates } from "../api/client";
import {
  DEFAULT_TELEMETRY_HISTORY_RANGE_KEY,
  getTelemetryHistoryRange,
  TELEMETRY_HISTORY_RANGES,
  TELEMETRY_TREND_STABILITY_PERCENT,
} from "../config/telemetryHistory";
import {
  calculateTelemetryYAxisDomain,
  summarizeThresholdAnalytics,
} from "../utils/telemetryAnalytics";

import type {
  AlertThreshold,
  SensorDiscovery,
  TelemetryAggregateBucket,
} from "../types/api";
import type { TelemetryHistoryRangeKey } from "../config/telemetryHistory";
import type { TooltipContentProps } from "recharts";

type HistoricalTelemetryProps = {
  machineId: string;
  thresholds: AlertThreshold[];
  thresholdLoading: boolean;
  thresholdError: string;
  onRetryThresholds: () => Promise<void>;
};

type LoadedRequestWindow = {
  start: string;
  end: string;
};

type HistoricalChartDatum = TelemetryAggregateBucket & {
  timestamp: number;
};

type LoadedHistory = {
  sensorId: string;
  rangeKey: TelemetryHistoryRangeKey;
  buckets: TelemetryAggregateBucket[];
  window: LoadedRequestWindow;
};

type TrendDirection = "Rising" | "Falling" | "Stable";

type WindowSummary = {
  average: number;
  minimum: number;
  maximum: number;
  readingCount: number;
  trend: TrendDirection;
  trendPercent: number | null;
};

const NUMBER_FORMATTER = new Intl.NumberFormat(undefined, {
  maximumFractionDigits: 2,
});
const TREND_FORMATTER = new Intl.NumberFormat(undefined, {
  maximumFractionDigits: 1,
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

function formatAxisTimestamp(
  timestamp: number,
  axisFormat: "time" | "day-time",
): string {
  const options: Intl.DateTimeFormatOptions =
    axisFormat === "time"
      ? { hour: "2-digit", minute: "2-digit" }
      : {
          month: "short",
          day: "numeric",
          hour: "2-digit",
          minute: "2-digit",
        };

  return new Date(timestamp).toLocaleString([], options);
}

function formatWindowTimestamp(timestamp: string): string {
  return new Date(timestamp).toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    second: "2-digit",
  });
}

function summarizeWindow(
  chartData: HistoricalChartDatum[],
): WindowSummary | null {
  if (chartData.length === 0) {
    return null;
  }

  const readingCount = chartData.reduce(
    (total, bucket) => total + bucket.count,
    0,
  );

  if (readingCount === 0) {
    return null;
  }

  const average =
    chartData.reduce(
      (total, bucket) => total + bucket.average * bucket.count,
      0,
    ) / readingCount;
  const minimum = Math.min(...chartData.map((bucket) => bucket.minimum));
  const maximum = Math.max(...chartData.map((bucket) => bucket.maximum));
  const firstAverage = chartData[0].average;
  const lastAverage = chartData[chartData.length - 1].average;
  const difference = lastAverage - firstAverage;
  const trendPercent =
    firstAverage === 0
      ? null
      : (difference / Math.abs(firstAverage)) * 100;
  const trend: TrendDirection =
    trendPercent !== null &&
    Math.abs(trendPercent) < TELEMETRY_TREND_STABILITY_PERCENT
      ? "Stable"
      : difference > 0
        ? "Rising"
        : difference < 0
          ? "Falling"
          : "Stable";

  return {
    average,
    minimum,
    maximum,
    readingCount,
    trend,
    trendPercent,
  };
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

function HistoricalTelemetry({
  machineId,
  thresholds,
  thresholdLoading,
  thresholdError,
  onRetryThresholds,
}: HistoricalTelemetryProps) {
  const [sensors, setSensors] = useState<SensorDiscovery[]>([]);
  const [selectedSensorId, setSelectedSensorId] = useState("");
  const [rangeKey, setRangeKey] =
    useState<TelemetryHistoryRangeKey>(
      DEFAULT_TELEMETRY_HISTORY_RANGE_KEY,
    );
  const [sensorRefreshVersion, setSensorRefreshVersion] = useState(0);
  const [refreshVersion, setRefreshVersion] = useState(0);
  const [sensorLoading, setSensorLoading] = useState(true);
  const [sensorError, setSensorError] = useState("");
  const [loadedHistory, setLoadedHistory] = useState<LoadedHistory | null>(
    null,
  );
  const [dataLoading, setDataLoading] = useState(false);
  const [dataError, setDataError] = useState("");

  const selectedRange = getTelemetryHistoryRange(rangeKey);
  const selectedSensor = sensors.find(
    (sensor) => sensor.id === selectedSensorId,
  );
  const matchingThreshold = thresholds.find(
    (threshold) => threshold.sensor_type === selectedSensor?.sensor_type,
  );
  const availableThreshold =
    !thresholdLoading && !thresholdError ? matchingThreshold : undefined;
  const currentHistory =
    loadedHistory?.sensorId === selectedSensorId &&
    loadedHistory.rangeKey === rangeKey
      ? loadedHistory
      : null;
  const chartData = useMemo<HistoricalChartDatum[]>(
    () =>
      (currentHistory?.buckets ?? [])
        .map((bucket) => ({
          ...bucket,
          timestamp: new Date(bucket.bucket_start).getTime(),
        }))
        .sort((left, right) => left.timestamp - right.timestamp),
    [currentHistory],
  );
  const windowSummary = useMemo(() => summarizeWindow(chartData), [chartData]);
  const thresholdAnalytics = useMemo(
    () =>
      availableThreshold
        ? summarizeThresholdAnalytics(
            currentHistory?.buckets ?? [],
            availableThreshold.threshold_value,
          )
        : null,
    [availableThreshold, currentHistory],
  );
  const yAxisDomain = useMemo(
    () =>
      calculateTelemetryYAxisDomain(
        currentHistory?.buckets ?? [],
        availableThreshold?.threshold_value,
      ),
    [availableThreshold, currentHistory],
  );

  useEffect(() => {
    const controller = new AbortController();
    let current = true;

    setSensors([]);
    setSelectedSensorId("");
    setSensorLoading(true);
    setSensorError("");
    setLoadedHistory(null);
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
      setDataLoading(false);
      return;
    }

    const controller = new AbortController();
    let current = true;
    const end = new Date();
    const start = new Date(end.getTime() - selectedRange.durationMs);
    const requestWindow: LoadedRequestWindow = {
      start: start.toISOString(),
      end: end.toISOString(),
    };

    setDataLoading(true);
    setDataError("");

    getTelemetryAggregates(
      {
        sensorId: selectedSensorId,
        start: requestWindow.start,
        end: requestWindow.end,
        bucket: selectedRange.bucket,
      },
      controller.signal,
    )
      .then((nextData) => {
        if (current) {
          setLoadedHistory({
            sensorId: selectedSensorId,
            rangeKey,
            buckets: nextData,
            window: requestWindow,
          });
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
  }, [rangeKey, refreshVersion, selectedRange, selectedSensorId]);

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
                setRangeKey(event.target.value as TelemetryHistoryRangeKey)
              }
            >
              {TELEMETRY_HISTORY_RANGES.map((range) => (
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

      {!sensorError &&
        selectedSensor &&
        dataLoading &&
        !currentHistory && (
          <div className="historical-state" role="status">
            Loading historical telemetry...
          </div>
        )}

      {!sensorError &&
        selectedSensor &&
        !dataLoading &&
        dataError &&
        !currentHistory && (
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

      {!sensorError && selectedSensor && currentHistory && (
        <div className="historical-window" aria-label="Loaded historical window">
          <span>Loaded window</span>
          <strong>
            {formatWindowTimestamp(currentHistory.window.start)} →{" "}
            {formatWindowTimestamp(currentHistory.window.end)}
          </strong>
          <span>Local time · {LOCAL_TIME_ZONE}</span>
        </div>
      )}

      {!sensorError && selectedSensor && currentHistory && dataLoading && (
        <div className="historical-notice" role="status">
          Refreshing historical telemetry. Showing the last loaded window.
        </div>
      )}

      {!sensorError && selectedSensor && (
        <aside
          className="historical-threshold-panel"
          aria-label="Operational threshold context"
        >
          <div className="historical-threshold-heading">
            <div>
              <p className="eyebrow">Operational context</p>
              <h3>Configured alert threshold</h3>
            </div>
            {availableThreshold && (
              <strong className="historical-threshold-value">
                {formatValue(
                  availableThreshold.threshold_value,
                  availableThreshold.unit,
                )}
              </strong>
            )}
          </div>

          {thresholdLoading && (
            <p className="historical-threshold-message" role="status">
              Loading configured threshold...
            </p>
          )}

          {!thresholdLoading && thresholdError && (
            <>
              <dl className="historical-threshold-metrics">
                <div>
                  <dt>Threshold status</dt>
                  <dd>Unavailable</dd>
                </div>
              </dl>
              <div className="historical-threshold-message error" role="alert">
                <span>
                  Unable to load the configured threshold. Historical telemetry
                  remains available. {thresholdError}
                </span>
                <button
                  className="view-all-button"
                  type="button"
                  onClick={() => void onRetryThresholds()}
                >
                  Try again
                </button>
              </div>
            </>
          )}

          {!thresholdLoading && !thresholdError && !matchingThreshold && (
            <>
              <dl className="historical-threshold-metrics">
                <div>
                  <dt>Threshold status</dt>
                  <dd>Unavailable</dd>
                </div>
              </dl>
              <p className="historical-threshold-message">
                No persisted threshold is configured for{" "}
                {selectedSensor.sensor_type}.
              </p>
            </>
          )}

          {availableThreshold && thresholdAnalytics && (
            <dl
              className="historical-threshold-metrics"
              aria-label="Threshold analysis for populated buckets"
            >
              <div>
                <dt>Threshold status</dt>
                <dd
                  className={
                    thresholdAnalytics.exceedingBucketCount > 0
                      ? "threshold-exceeded"
                      : "threshold-within"
                  }
                >
                  {thresholdAnalytics.exceedingBucketCount > 0
                    ? "Threshold exceeded"
                    : "Within configured threshold"}
                </dd>
              </div>
              <div>
                <dt>Buckets exceeding</dt>
                <dd>
                  {thresholdAnalytics.exceedingBucketCount.toLocaleString()} of{" "}
                  {chartData.length.toLocaleString()}
                </dd>
              </div>
              <div>
                <dt>Share of populated buckets</dt>
                <dd>
                  {TREND_FORMATTER.format(
                    thresholdAnalytics.exceedingBucketPercentage,
                  )}
                  %
                </dd>
              </div>
              <div>
                <dt>Readings in exceeding buckets</dt>
                <dd>
                  {thresholdAnalytics.readingsInExceedingBuckets.toLocaleString()}
                </dd>
              </div>
              <div>
                <dt>Peak bucket maximum</dt>
                <dd>
                  {formatValue(
                    thresholdAnalytics.peakMaximum,
                    availableThreshold.unit,
                  )}
                  <small>
                    {formatLocalTimestamp(
                      Date.parse(thresholdAnalytics.peakBucketStart),
                    )}
                  </small>
                </dd>
              </div>
            </dl>
          )}

          {availableThreshold && currentHistory && chartData.length === 0 && (
            <p className="historical-threshold-message">
              No populated buckets are available for threshold analysis.
            </p>
          )}
        </aside>
      )}

      {!sensorError &&
        selectedSensor &&
        currentHistory &&
        !dataLoading &&
        dataError && (
          <div className="historical-notice error" role="alert">
            <span>
              Refresh failed. Showing the last successfully loaded window.
              {" "}
              {dataError}
            </span>
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
        currentHistory &&
        chartData.length === 0 && (
          <div className="historical-state">
            No historical telemetry found for this sensor and time range.
          </div>
        )}

      {!sensorError &&
        selectedSensor &&
        currentHistory &&
        chartData.length > 0 && (
          <article
            className="historical-chart-card"
            aria-describedby="historical-chart-context"
          >
            <div className="historical-chart-summary">
              <div>
                <strong>{selectedSensor.name}</strong>
                <span>
                  {selectedSensor.sensor_type} · {selectedSensor.unit} ·{" "}
                  {selectedRange.label} · {selectedRange.bucket} buckets
                </span>
              </div>
              <span>{chartData.length.toLocaleString()} populated buckets</span>
            </div>

            <p
              id="historical-chart-context"
              className="historical-chart-context"
            >
              Chart showing average, minimum, and maximum values for each
              populated bucket
              {availableThreshold
                ? `, with the configured threshold at ${formatValue(
                    availableThreshold.threshold_value,
                    availableThreshold.unit,
                  )}`
                : ""}
              .
            </p>

            {windowSummary && (
              <dl className="historical-metrics" aria-label="Window summary">
                <div>
                  <dt>Average</dt>
                  <dd>
                    {formatValue(windowSummary.average, selectedSensor.unit)}
                  </dd>
                </div>
                <div>
                  <dt>Minimum</dt>
                  <dd>
                    {formatValue(windowSummary.minimum, selectedSensor.unit)}
                  </dd>
                </div>
                <div>
                  <dt>Maximum</dt>
                  <dd>
                    {formatValue(windowSummary.maximum, selectedSensor.unit)}
                  </dd>
                </div>
                <div>
                  <dt>Readings</dt>
                  <dd>{windowSummary.readingCount.toLocaleString()}</dd>
                </div>
                <div>
                  <dt>Trend</dt>
                  <dd className={`trend-${windowSummary.trend.toLowerCase()}`}>
                    {windowSummary.trend}
                    {windowSummary.trendPercent === null
                      ? " · percentage unavailable"
                      : ` ${TREND_FORMATTER.format(
                          Math.abs(windowSummary.trendPercent),
                        )}%`}
                  </dd>
                </div>
              </dl>
            )}

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
                      formatAxisTimestamp(timestamp, selectedRange.axisFormat)
                    }
                    stroke="#64748b"
                    minTickGap={selectedRange.axisMinTickGap}
                  />
                  <YAxis
                    domain={yAxisDomain}
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
                  {availableThreshold && (
                    <ReferenceLine
                      y={availableThreshold.threshold_value}
                      stroke="#a78bfa"
                      strokeWidth={1.5}
                      strokeDasharray="6 4"
                      label={{
                        value: `Threshold · ${formatValue(
                          availableThreshold.threshold_value,
                          availableThreshold.unit,
                        )}`,
                        position: "insideTopRight",
                        fill: "#c4b5fd",
                        fontSize: 12,
                      }}
                    />
                  )}
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
