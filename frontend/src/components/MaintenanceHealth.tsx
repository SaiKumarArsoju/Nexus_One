import { useEffect, useMemo, useRef, useState } from "react";

import { getMachineHealthScore } from "../api/client";
import {
  DEFAULT_HEALTH_SCORE_WINDOW,
  HEALTH_SCORE_WINDOWS,
} from "../config/healthScore";
import type {
  HealthBand,
  HealthScoreWindow,
  MachineHealthScore,
  SensorHealthPenalty,
} from "../types/api";

type MaintenanceHealthProps = { machineId: string };
type LoadedScore = {
  machineId: string;
  window: HealthScoreWindow;
  data: MachineHealthScore;
};

const PENALTY_LABELS: ReadonlyArray<[keyof SensorHealthPenalty, string]> = [
  ["threshold_proximity", "Threshold proximity"],
  ["mean_level", "Mean level"],
  ["exceedance", "Exceedance"],
  ["trend", "Trend"],
  ["variability", "Variability"],
];

function formatScore(value: number | null): string {
  return value === null ? "Insufficient data" : `${value.toFixed(1)} / 100`;
}

function displayEnum(value: string): string {
  return value.replaceAll("_", " ");
}

function formatTimestamp(value: string): string {
  return new Date(value).toLocaleString();
}

function bandClass(band: HealthBand): string {
  return `maintenance-band ${band.toLowerCase().replaceAll("_", "-")}`;
}

function MaintenanceHealth({ machineId }: MaintenanceHealthProps) {
  const [window, setWindow] = useState<HealthScoreWindow>(DEFAULT_HEALTH_SCORE_WINDOW);
  const [requestVersion, setRequestVersion] = useState(0);
  const [loadedScore, setLoadedScore] = useState<LoadedScore | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const requestIdentity = useRef(0);

  const currentScore =
    loadedScore?.machineId === machineId && loadedScore.window === window
      ? loadedScore.data
      : null;

  useEffect(() => {
    const controller = new AbortController();
    const identity = ++requestIdentity.current;
    let current = true;
    setLoading(true);
    setError("");

    getMachineHealthScore({ machineId, window, signal: controller.signal })
      .then((data) => {
        if (current && identity === requestIdentity.current) {
          setLoadedScore({ machineId, window, data });
        }
      })
      .catch((requestError: unknown) => {
        if (
          current &&
          identity === requestIdentity.current &&
          !(requestError instanceof DOMException && requestError.name === "AbortError")
        ) {
          setError(
            requestError instanceof Error
              ? requestError.message
              : "Unable to load maintenance health.",
          );
        }
      })
      .finally(() => {
        if (current && identity === requestIdentity.current) {
          setLoading(false);
        }
      });

    return () => {
      current = false;
      controller.abort();
    };
  }, [machineId, window, requestVersion]);

  const mostConcerningName = useMemo(() => {
    if (!currentScore?.most_concerning_sensor_id) return "Unavailable";
    return (
      currentScore.sensor_scores.find(
        (sensor) => sensor.sensor_id === currentScore.most_concerning_sensor_id,
      )?.sensor_name ?? "Unavailable"
    );
  }, [currentScore]);

  const refresh = () => {
    if (!loading) setRequestVersion((version) => version + 1);
  };

  return (
    <section className="section maintenance-health" aria-labelledby="maintenance-health-heading">
      <div className="maintenance-heading">
        <div>
          <p className="eyebrow">DETERMINISTIC HEALTH INDICATOR</p>
          <h2 id="maintenance-health-heading">Maintenance Health</h2>
          <p className="maintenance-disclaimer">
            Deterministic maintenance indicator based on recent telemetry and configured
            thresholds. It is not a failure probability or remaining-useful-life prediction.
          </p>
        </div>
        <div className="maintenance-controls">
          <label>
            Scoring window
            <select
              value={window}
              onChange={(event) => setWindow(event.target.value as HealthScoreWindow)}
              disabled={loading}
            >
              {HEALTH_SCORE_WINDOWS.map((option) => (
                <option key={option.key} value={option.key}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <button className="view-all-button" onClick={refresh} disabled={loading}>
            {loading && currentScore ? "Refreshing..." : "Refresh"}
          </button>
        </div>
      </div>

      {loading && !currentScore && (
        <div className="maintenance-state" role="status">Loading maintenance health...</div>
      )}
      {error && !currentScore && (
        <div className="maintenance-state error" role="alert">
          <span>Unable to load maintenance health: {error}</span>
          <button className="view-all-button" onClick={refresh}>Retry</button>
        </div>
      )}
      {error && currentScore && (
        <div className="maintenance-notice error" role="alert">
          Refresh failed. Showing the last successful scoring window. {error}
        </div>
      )}
      {loading && currentScore && (
        <div className="maintenance-notice" role="status">
          Refreshing maintenance health while the last result remains visible.
        </div>
      )}

      {currentScore && (
        <>
          <div className="maintenance-summary">
            <div className="maintenance-score-card">
              <span>Health score</span>
              <strong>{formatScore(currentScore.health_score)}</strong>
              <span className={bandClass(currentScore.health_band)}>
                {displayEnum(currentScore.health_band)}
              </span>
            </div>
            <dl className="maintenance-summary-grid">
              <div><dt>Data confidence</dt><dd>{currentScore.confidence}</dd></div>
              <div><dt>Scored sensors</dt><dd>{currentScore.scored_sensor_count} of {currentScore.total_sensor_count}</dd></div>
              <div><dt>Lowest sensor score</dt><dd>{formatScore(currentScore.lowest_sensor_score)}</dd></div>
              <div><dt>Most concerning sensor</dt><dd>{mostConcerningName}</dd></div>
            </dl>
          </div>
          <p className="maintenance-confidence-note">
            Confidence reflects telemetry coverage, not machine condition.
          </p>
          <div className="maintenance-metadata">
            <span><strong>Scoring window:</strong> {formatTimestamp(currentScore.window_start)} – {formatTimestamp(currentScore.window_end)}</span>
            <span>Feature {currentScore.feature_version} · Scoring {currentScore.scoring_version}</span>
          </div>
          <div className="maintenance-reasons">
            <h3>Machine explanation</h3>
            <ul>{currentScore.reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul>
          </div>
          <div className="maintenance-sensors">
            <h3>Sensor health breakdown</h3>
            {currentScore.sensor_scores.map((sensor) => (
              <article
                className={`maintenance-sensor-card${sensor.sensor_id === currentScore.most_concerning_sensor_id ? " concerning" : ""}`}
                key={sensor.sensor_id}
              >
                <header>
                  <div><strong>{sensor.sensor_name}</strong><span>{displayEnum(sensor.sensor_type)} · {sensor.unit}</span></div>
                  <div className="maintenance-sensor-score"><strong>{formatScore(sensor.health_score)}</strong><span className={bandClass(sensor.health_band)}>{displayEnum(sensor.health_band)}</span></div>
                </header>
                <dl className="maintenance-sensor-meta">
                  <div><dt>Confidence</dt><dd>{sensor.confidence}</dd></div>
                  <div><dt>Coverage</dt><dd>{displayEnum(sensor.coverage_status)}</dd></div>
                  <div><dt>Configured threshold</dt><dd>{sensor.threshold_value.toLocaleString()} {sensor.unit}</dd></div>
                </dl>
                <div className="maintenance-penalties">
                  <h4>Score deductions</h4>
                  <dl>{PENALTY_LABELS.map(([key, label]) => <div key={key}><dt>{label}</dt><dd>{sensor.component_penalties[key].toFixed(1)} pts</dd></div>)}</dl>
                </div>
                <div className="maintenance-sensor-reasons">
                  <h4>Explanation</h4>
                  <ul>{sensor.reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul>
                </div>
              </article>
            ))}
          </div>
        </>
      )}
    </section>
  );
}

export default MaintenanceHealth;
