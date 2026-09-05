import type { TelemetryAggregationBucket } from "../types/api";

export type TelemetryHistoryRangeKey = "1h" | "6h" | "24h" | "7d" | "30d";

export type TelemetryHistoryRange = {
  key: TelemetryHistoryRangeKey;
  label: string;
  durationMs: number;
  bucket: TelemetryAggregationBucket;
  axisFormat: "time" | "day-time";
  axisMinTickGap: number;
};

const MINUTE_MS = 60_000;
const HOUR_MS = 60 * MINUTE_MS;
const DAY_MS = 24 * HOUR_MS;

export const TELEMETRY_HISTORY_RANGES: readonly TelemetryHistoryRange[] = [
  {
    key: "1h",
    label: "Last 1 hour",
    durationMs: HOUR_MS,
    bucket: "1m",
    axisFormat: "time",
    axisMinTickGap: 48,
  },
  {
    key: "6h",
    label: "Last 6 hours",
    durationMs: 6 * HOUR_MS,
    bucket: "5m",
    axisFormat: "time",
    axisMinTickGap: 52,
  },
  {
    key: "24h",
    label: "Last 24 hours",
    durationMs: DAY_MS,
    bucket: "15m",
    axisFormat: "time",
    axisMinTickGap: 58,
  },
  {
    key: "7d",
    label: "Last 7 days",
    durationMs: 7 * DAY_MS,
    bucket: "1h",
    axisFormat: "day-time",
    axisMinTickGap: 66,
  },
  {
    key: "30d",
    label: "Last 30 days",
    durationMs: 30 * DAY_MS,
    bucket: "1h",
    axisFormat: "day-time",
    axisMinTickGap: 72,
  },
];

export const DEFAULT_TELEMETRY_HISTORY_RANGE_KEY: TelemetryHistoryRangeKey =
  "1h";

export const TELEMETRY_TREND_STABILITY_PERCENT = 1;

export function getTelemetryHistoryRange(
  key: TelemetryHistoryRangeKey,
): TelemetryHistoryRange {
  return (
    TELEMETRY_HISTORY_RANGES.find((range) => range.key === key) ??
    TELEMETRY_HISTORY_RANGES[0]
  );
}
