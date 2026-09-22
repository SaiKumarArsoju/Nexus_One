import { useEffect, useRef, useState } from "react";

import { getMachineMaintenanceAssessment } from "../api/client";
import {
  DEFAULT_HEALTH_SCORE_WINDOW,
  HEALTH_SCORE_WINDOWS,
} from "../config/healthScore";
import type {
  HealthScoreWindow,
  MachineMaintenanceAssessment,
  MaintenancePriority,
  RecommendedMaintenanceAction,
} from "../types/api";

type MaintenanceAssessmentProps = { machineId: string };
type LoadedAssessment = {
  machineId: string;
  window: HealthScoreWindow;
  data: MachineMaintenanceAssessment;
};

const ACTION_LABELS: Record<RecommendedMaintenanceAction, string> = {
  CONTINUE_MONITORING: "Continue monitoring",
  REVIEW_OPERATING_CONDITIONS: "Review operating conditions",
  INSPECT_MACHINE: "Inspect machine",
  INSPECT_SENSOR_OR_COMPONENT: "Inspect sensor or component",
  SCHEDULE_MAINTENANCE_REVIEW: "Schedule maintenance review",
  IMMEDIATE_OPERATIONAL_REVIEW: "Immediate operational review",
  VERIFY_TELEMETRY: "Verify telemetry",
};

const PRIORITY_MESSAGES: Record<MaintenancePriority, string> = {
  NONE: "No maintenance attention is currently indicated by the deterministic policy.",
  LOW: "Continue monitoring and review operating conditions when practical.",
  MEDIUM: "Maintenance attention should be planned.",
  HIGH: "Prompt inspection is recommended.",
  CRITICAL: "Immediate operational review is recommended.",
  INSUFFICIENT_DATA: "Insufficient data to assess maintenance priority.",
};

function displayEnum(value: string): string {
  return value.replaceAll("_", " ");
}

function formatScore(value: number | null): string {
  return value === null ? "Insufficient data" : `${value.toFixed(1)} / 100`;
}

function formatTimestamp(value: string): string {
  return new Date(value).toLocaleString();
}

function MaintenanceAssessment({ machineId }: MaintenanceAssessmentProps) {
  const [window, setWindow] = useState<HealthScoreWindow>(DEFAULT_HEALTH_SCORE_WINDOW);
  const [requestVersion, setRequestVersion] = useState(0);
  const [loadedAssessment, setLoadedAssessment] = useState<LoadedAssessment | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const requestIdentity = useRef(0);

  const currentAssessment =
    loadedAssessment?.machineId === machineId && loadedAssessment.window === window
      ? loadedAssessment.data
      : null;

  useEffect(() => {
    const controller = new AbortController();
    const identity = ++requestIdentity.current;
    let current = true;
    setLoading(true);
    setError("");

    getMachineMaintenanceAssessment({ machineId, window, signal: controller.signal })
      .then((data) => {
        if (current && identity === requestIdentity.current) {
          setLoadedAssessment({ machineId, window, data });
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
              : "Unable to load maintenance assessment.",
          );
        }
      })
      .finally(() => {
        if (current && identity === requestIdentity.current) setLoading(false);
      });

    return () => {
      current = false;
      controller.abort();
    };
  }, [machineId, window, requestVersion]);

  const refresh = () => {
    if (!loading) setRequestVersion((version) => version + 1);
  };

  return (
    <section
      className="section maintenance-assessment"
      aria-labelledby="maintenance-assessment-heading"
    >
      <div className="maintenance-heading">
        <div>
          <p className="eyebrow">DETERMINISTIC MAINTENANCE ATTENTION</p>
          <h2 id="maintenance-assessment-heading">Maintenance Assessment</h2>
          <p className="maintenance-disclaimer">
            Priority reflects deterministic maintenance-attention policy using current health and
            unresolved alert evidence. It is not a failure probability, diagnosis, or
            remaining-useful-life prediction.
          </p>
        </div>
        <div className="maintenance-controls">
          <label>
            Assessment window
            <select
              value={window}
              onChange={(event) => setWindow(event.target.value as HealthScoreWindow)}
              disabled={loading}
            >
              {HEALTH_SCORE_WINDOWS.map((option) => (
                <option key={option.key} value={option.key}>{option.label}</option>
              ))}
            </select>
          </label>
          <button className="view-all-button" onClick={refresh} disabled={loading}>
            {loading && currentAssessment ? "Refreshing..." : "Refresh"}
          </button>
        </div>
      </div>

      {loading && !currentAssessment && (
        <div className="maintenance-state" role="status">Loading maintenance assessment...</div>
      )}
      {error && !currentAssessment && (
        <div className="maintenance-state error" role="alert">
          <span>Unable to load maintenance assessment: {error}</span>
          <button className="view-all-button" onClick={refresh}>Retry</button>
        </div>
      )}
      {error && currentAssessment && (
        <div className="maintenance-notice error" role="alert">
          Refresh failed. Showing the last successful assessment window. {error}
        </div>
      )}
      {loading && currentAssessment && (
        <div className="maintenance-notice" role="status">
          Refreshing assessment while the last result remains visible.
        </div>
      )}

      {currentAssessment && (
        <>
          <div className="assessment-summary">
            <div className="assessment-priority-card">
              <span>Maintenance priority</span>
              <strong>{displayEnum(currentAssessment.maintenance_priority)}</strong>
              <span className={`assessment-priority ${currentAssessment.maintenance_priority.toLowerCase().replaceAll("_", "-")}`}>
                {PRIORITY_MESSAGES[currentAssessment.maintenance_priority]}
              </span>
            </div>
            <dl className="assessment-summary-grid">
              <div><dt>Health context</dt><dd>{formatScore(currentAssessment.health_score)} · {displayEnum(currentAssessment.health_band)}</dd></div>
              <div><dt>Telemetry confidence</dt><dd>{currentAssessment.confidence}</dd></div>
              <div><dt>Unresolved alerts</dt><dd>{currentAssessment.unresolved_alert_count}</dd></div>
              <div><dt>Critical alerts</dt><dd>{currentAssessment.critical_alert_count}</dd></div>
              <div><dt>Warning alerts</dt><dd>{currentAssessment.warning_alert_count}</dd></div>
              <div><dt>Most concerning sensor</dt><dd>{currentAssessment.most_concerning_sensor_name ?? "Unavailable"}</dd></div>
            </dl>
          </div>
          <p className="maintenance-confidence-note">
            Telemetry confidence describes coverage; it is distinct from maintenance priority.
          </p>
          {currentAssessment.unresolved_alert_count === 0 && (
            <p className="assessment-zero-alerts">No unresolved alerts contribute to this assessment.</p>
          )}
          <div className="maintenance-metadata">
            <span><strong>Assessment window:</strong> {formatTimestamp(currentAssessment.window_start)} – {formatTimestamp(currentAssessment.window_end)}</span>
            <span>Feature {currentAssessment.feature_version} · Scoring {currentAssessment.scoring_version} · Policy {currentAssessment.maintenance_policy_version}</span>
          </div>
          <div className="assessment-columns">
            <div>
              <h3>Recommended actions</h3>
              <ul className="assessment-actions">
                {currentAssessment.recommended_actions.map((action) => (
                  <li key={action}>{ACTION_LABELS[action]}</li>
                ))}
              </ul>
            </div>
            <div>
              <h3>Why this priority?</h3>
              {currentAssessment.evidence.length ? (
                <ul className="assessment-evidence">
                  {currentAssessment.evidence.map((item, index) => (
                    <li key={`${item.type}-${item.alert_id ?? item.sensor_id ?? index}`}>
                      <strong>{displayEnum(item.type)}</strong>
                      {item.severity && <span>{item.severity}</span>}
                      {item.sensor_name && <span>{item.sensor_name}</span>}
                      <p>{item.message}</p>
                    </li>
                  ))}
                </ul>
              ) : <p className="assessment-empty">No concern evidence was returned.</p>}
            </div>
          </div>
          <div className="maintenance-reasons">
            <h3>Assessment explanation</h3>
            <ul>{currentAssessment.reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul>
          </div>
        </>
      )}
    </section>
  );
}

export default MaintenanceAssessment;
