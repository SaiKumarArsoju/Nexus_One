import { useState } from "react";

import type {
  AlertThreshold,
  SensorType,
} from "../types/api";

type AlertThresholdsPageProps = {
  thresholds: AlertThreshold[];
  error: string;
  loading: boolean;
  onUpdateThreshold: (
    sensorType: SensorType,
    thresholdValue: number,
  ) => Promise<AlertThreshold>;
};

type ThresholdCardProps = {
  threshold: AlertThreshold;
  onUpdateThreshold: AlertThresholdsPageProps["onUpdateThreshold"];
};

const SENSOR_LABELS: Record<SensorType, string> = {
  TEMPERATURE: "Temperature",
  PRESSURE: "Pressure",
  VIBRATION: "Vibration",
  RPM: "RPM",
  ENERGY: "Energy",
};

function ThresholdCard({
  threshold,
  onUpdateThreshold,
}: ThresholdCardProps) {
  const [draftValue, setDraftValue] = useState(
    String(threshold.threshold_value),
  );
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  const trimmedValue = draftValue.trim();
  const parsedValue = Number(trimmedValue);
  const validationError =
    trimmedValue === "" || !Number.isFinite(parsedValue)
      ? "Enter a valid numeric threshold."
      : parsedValue <= 0
        ? "Threshold must be greater than zero."
        : "";
  const hasChanges =
    validationError === "" &&
    parsedValue !== threshold.threshold_value;
  const canSubmit = hasChanges && !saving;
  const inputId = `threshold-${threshold.sensor_type.toLowerCase()}`;
  const messageId = `${inputId}-message`;

  async function handleSubmit(
    event: React.FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    if (!canSubmit) {
      return;
    }

    setSaving(true);
    setSaveError("");
    setSuccessMessage("");

    try {
      const updatedThreshold = await onUpdateThreshold(
        threshold.sensor_type,
        parsedValue,
      );

      setDraftValue(String(updatedThreshold.threshold_value));
      setSuccessMessage("Threshold updated.");
    } catch (error) {
      setSaveError(
        error instanceof Error
          ? error.message
          : "Failed to update threshold.",
      );
    } finally {
      setSaving(false);
    }
  }

  function handleDraftChange(value: string) {
    setDraftValue(value);
    setSaveError("");
    setSuccessMessage("");
  }

  let stateMessage = "Saved value.";
  let stateClassName = "threshold-state neutral";

  if (validationError) {
    stateMessage = validationError;
    stateClassName = "threshold-state error";
  } else if (saving) {
    stateMessage = "Saving threshold...";
    stateClassName = "threshold-state saving";
  } else if (saveError) {
    stateMessage = saveError;
    stateClassName = "threshold-state error";
  } else if (successMessage) {
    stateMessage = successMessage;
    stateClassName = "threshold-state success";
  } else if (hasChanges) {
    stateMessage = "Unsaved change.";
    stateClassName = "threshold-state editing";
  }

  return (
    <article
      className={`threshold-card ${threshold.severity.toLowerCase()}`}
    >
      <div className="threshold-card-header">
        <div>
          <p className="threshold-sensor-type">
            {SENSOR_LABELS[threshold.sensor_type]}
          </p>
          <p className="threshold-alert-type">
            {threshold.alert_type.replaceAll("_", " ")}
          </p>
        </div>

        <span
          className={`health-badge ${threshold.severity.toLowerCase()}`}
        >
          {threshold.severity}
        </span>
      </div>

      <div className="threshold-current">
        <span>Current threshold</span>
        <strong>
          {threshold.threshold_value.toLocaleString()}{" "}
          <small>{threshold.unit}</small>
        </strong>
      </div>

      <form className="threshold-form" onSubmit={handleSubmit}>
        <div className="threshold-input-group">
          <label htmlFor={inputId}>
            New threshold ({threshold.unit})
          </label>

          <input
            id={inputId}
            className="threshold-input"
            type="number"
            inputMode="decimal"
            min="0"
            step="any"
            value={draftValue}
            aria-describedby={messageId}
            aria-invalid={validationError !== ""}
            onChange={(event) =>
              handleDraftChange(event.target.value)
            }
          />
        </div>

        <button
          className="threshold-update-button"
          type="submit"
          disabled={!canSubmit}
        >
          {saving ? "Updating..." : "Update"}
        </button>
      </form>

      <p
        id={messageId}
        className={stateClassName}
        role={
          validationError || saveError
            ? "alert"
            : "status"
        }
      >
        {stateMessage}
      </p>

      <p className="threshold-updated-at">
        Last updated{" "}
        <time dateTime={threshold.updated_at}>
          {new Date(threshold.updated_at).toLocaleString()}
        </time>
      </p>
    </article>
  );
}

function AlertThresholdsPage({
  thresholds,
  error,
  loading,
  onUpdateThreshold,
}: AlertThresholdsPageProps) {
  if (error) {
    return (
      <div className="status-message">
        Error loading alert thresholds: {error}
      </div>
    );
  }

  if (loading) {
    return (
      <div className="status-message">
        Loading alert thresholds...
      </div>
    );
  }

  return (
    <>
      <header className="page-header">
        <div>
          <p className="eyebrow">Operational Configuration</p>
          <h1>Alert Thresholds</h1>
          <p className="subtitle">
            Configure operational limits used by alerts, machine health,
            and dashboard status calculations.
          </p>
        </div>
      </header>

      <aside className="threshold-info-note">
        Threshold changes apply to subsequent operational evaluations.
        Existing alerts are not automatically recalculated.
      </aside>

      {thresholds.length === 0 ? (
        <p className="no-warnings">
          No alert thresholds configured.
        </p>
      ) : (
        <section
          className="thresholds-grid"
          aria-label="Alert threshold settings"
        >
          {thresholds.map((threshold) => (
            <ThresholdCard
              key={threshold.sensor_type}
              threshold={threshold}
              onUpdateThreshold={onUpdateThreshold}
            />
          ))}
        </section>
      )}
    </>
  );
}

export default AlertThresholdsPage;
