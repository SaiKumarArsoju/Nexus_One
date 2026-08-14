import { useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";

import MetricCard from "../components/MetricCard";
import TrendChart from "../components/TrendChart";

import type {
  MachineDetail,
  MachineTrends,
} from "../types/api";

type MachineDetailRouteProps = {
  machine: MachineDetail | null;
  error: string;
  trends: MachineTrends | null;
  trendsError: string;
  setSelectedMachineId: (machineId: string | null) => void;
};

function MachineDetailRoute({
  machine,
  error,
  trends,
  trendsError,
  setSelectedMachineId,
}: MachineDetailRouteProps) {
  const { machineId } = useParams();
  const navigate = useNavigate();

  useEffect(() => {
    setSelectedMachineId(machineId ?? null);

    return () => {
      setSelectedMachineId(null);
    };
  }, [machineId, setSelectedMachineId]);

  return (
    <MachineDetailPage
      machine={machine}
      error={error}
      trends={trends}
      trendsError={trendsError}
      onBack={() => navigate("/machines")}
    />
  );
}

type MachineDetailPageProps = {
  machine: MachineDetail | null;
  error: string;
  trends: MachineTrends | null;
  trendsError: string;
  onBack: () => void;
};

function MachineDetailPage({
  machine,
  error,
  trends,
  trendsError,
  onBack,
}: MachineDetailPageProps) {
  if (error) {
    return <div className="status-message">Error: {error}</div>;
  }

  if (!machine) {
    return (
      <div className="status-message">
        Loading machine details...
      </div>
    );
  }

  return (
    <>
      <button className="back-button" onClick={onBack}>
        ← Back to Machines
      </button>

      <header className="page-header">
        <div>
          <p className="eyebrow">{machine.production_line}</p>
          <h1>{machine.name}</h1>
          <p className="subtitle">
            Serial: {machine.serial_number}
          </p>
        </div>

        <span
          className={`health-badge ${machine.health_status.toLowerCase()}`}
        >
          {machine.health_status}
        </span>
      </header>

      <section className="grid">
        <MetricCard
          label="Health Score"
          value={`${machine.health_score}%`}
        />

        <MetricCard
          label="Temperature"
          value={machine.temperature ?? "—"}
        />

        <MetricCard
          label="Pressure"
          value={machine.pressure ?? "—"}
        />

        <MetricCard
          label="Vibration"
          value={machine.vibration ?? "—"}
        />

        <MetricCard
          label="RPM"
          value={machine.rpm ?? "—"}
        />

        <MetricCard
          label="Energy"
          value={machine.energy ?? "—"}
        />
      </section>

      <section className="section">
        <h2>Warnings</h2>

        {machine.warnings.length === 0 ? (
          <p className="no-warnings">
            No active machine warnings.
          </p>
        ) : (
          <div className="warning-list">
            {machine.warnings.map((warning) => (
              <div
                className="warning-item"
                key={warning}
              >
                {warning}
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="section">
        <h2>Telemetry Trends</h2>

        {trendsError && (
          <p className="no-warnings">
            Error loading trends: {trendsError}
          </p>
        )}

        {!trends && !trendsError && (
          <p className="no-warnings">
            Loading telemetry trends...
          </p>
        )}

        {trends && (
          <div className="charts-grid">
            <TrendChart
              title="Temperature"
              data={trends.temperature}
            />

            <TrendChart
              title="Pressure"
              data={trends.pressure}
            />

            <TrendChart
              title="Vibration"
              data={trends.vibration}
            />

            <TrendChart
              title="RPM"
              data={trends.rpm}
            />

            <TrendChart
              title="Energy"
              data={trends.energy}
            />
          </div>
        )}
      </section>
    </>
  );
}

export default MachineDetailRoute;
