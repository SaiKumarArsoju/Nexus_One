import { TELEMETRY_HISTORY_RANGES } from "./telemetryHistory";
import type { HealthScoreWindow } from "../types/api";

export const DEFAULT_HEALTH_SCORE_WINDOW: HealthScoreWindow = "24h";

export const HEALTH_SCORE_WINDOWS = TELEMETRY_HISTORY_RANGES.filter(
  (range): range is typeof range & { key: HealthScoreWindow } => range.key !== "30d",
).map(({ key, label }) => ({ key, label }));
