import { useEffect, useState } from "react";
import "./App.css";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type Page = "dashboard" | "machines" | "alerts";

type DashboardSummary = {
  factories: number;
  production_lines: number;
  machines: number;
  sensors: number;
  sensor_readings: number;
  healthy_machines: number;
  warning_machines: number;
  critical_machines: number;
  active_alerts: number;
  warning_alerts: number;
  critical_alerts: number;
  resolved_alerts: number;
};

type MachineFleetItem = {
  id: string;
  name: string;
  serial_number: string;
  production_line: string;
  health_status: string;
  health_score: number;
};

type MachineDetail = {
  id: string;
  name: string;
  serial_number: string;
  production_line: string;
  health_status: string;
  health_score: number;
  temperature: number | null;
  pressure: number | null;
  vibration: number | null;
  rpm: number | null;
  energy: number | null;
  warnings: string[];
};

type TelemetryTrendPoint = {
  recorded_at: string;
  value: number;
};

type MachineTrends = {
  machine_id: string;
  machine_name: string;
  temperature: TelemetryTrendPoint[];
  pressure: TelemetryTrendPoint[];
  vibration: TelemetryTrendPoint[];
  rpm: TelemetryTrendPoint[];
  energy: TelemetryTrendPoint[];
};

type AlertItem = {
  id: string;
  machine_id: string;
  machine_name: string;
  severity: string;
  status: string;
  alert_type: string;
  message: string;
  created_at: string;
};

function App() {
  const [page, setPage] = useState<Page>("dashboard");
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [error, setError] = useState("");
  const [machines, setMachines] = useState<MachineFleetItem[]>([]);
  const [machinesError, setMachinesError] = useState("");
  const [selectedMachineId, setSelectedMachineId] = useState<string | null>(null);
  const [machineDetail, setMachineDetail] = useState<MachineDetail | null>(null);
  const [machineDetailError, setMachineDetailError] = useState("");
  const [machineTrends, setMachineTrends] = useState<MachineTrends | null>(null);
  const [machineTrendsError, setMachineTrendsError] = useState("");
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [alertsError, setAlertsError] = useState("");

  useEffect(() => {
    fetch("http://127.0.0.1:8000/api/v1/alerts")
      .then((response) => {
        if (!response.ok) {
          throw new Error("Failed to load alerts");
        }

        return response.json();
      })
      .then((data: AlertItem[]) => {
        setAlerts(data);
      })
      .catch((err: Error) => {
        setAlertsError(err.message);
      });
  }, []);

  useEffect(() => {
    if (!selectedMachineId) {
      return;
    }

    setMachineTrends(null);
    setMachineTrendsError("");

    fetch(
      `http://127.0.0.1:8000/api/v1/machines/${selectedMachineId}/trends`,
    )
      .then((response) => {
        if (!response.ok) {
          throw new Error("Failed to load telemetry trends");
        }

        return response.json();
      })
      .then((data: MachineTrends) => {
        setMachineTrends(data);
      })
      .catch((err: Error) => {
        setMachineTrendsError(err.message);
      });
  }, [selectedMachineId]);

  useEffect(() => {
    if (!selectedMachineId) {
      return;
    }

    setMachineDetail(null);
    setMachineDetailError("");

    fetch(`http://127.0.0.1:8000/api/v1/machines/${selectedMachineId}`)
      .then((response) => {
        if (!response.ok) {
          throw new Error("Failed to load machine details");
        }

        return response.json();
      })
      .then((data: MachineDetail) => {
        setMachineDetail(data);
      })
      .catch((err: Error) => {
        setMachineDetailError(err.message);
      });
  }, [selectedMachineId]);

  useEffect(() => {
    fetch("http://127.0.0.1:8000/api/v1/dashboard/summary")
      .then((response) => {
        if (!response.ok) {
          throw new Error("Failed to load dashboard data");
        }

        return response.json();
      })
      .then((data: DashboardSummary) => {
        setSummary(data);
      })
      .catch((err: Error) => {
        setError(err.message);
      });
  }, []);
  useEffect(() => {
    fetch("http://127.0.0.1:8000/api/v1/machines")
      .then((response) => {
        if (!response.ok) {
          throw new Error("Failed to load machines");
        }

        return response.json();
      })
      .then((data: MachineFleetItem[]) => {
        setMachines(data);
      })
      .catch((err: Error) => {
        setMachinesError(err.message);
      });
  }, []);
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">N1</span>

          <div>
            <strong>NEXUS ONE</strong>
            <small>Industrial Intelligence</small>
          </div>
        </div>

        <nav className="nav">
          <button
            className={page === "dashboard" ? "nav-item active" : "nav-item"}
            onClick={() => setPage("dashboard")}
          >
            Dashboard
          </button>

          <button
            className={page === "machines" ? "nav-item active" : "nav-item"}
            onClick={() => setPage("machines")}
          >
            Machines
          </button>

          <button
            className={page === "alerts" ? "nav-item active" : "nav-item"}
            onClick={() => setPage("alerts")}
          >
            Alerts
          </button>
        </nav>

        <div className="sidebar-status">
          <span className="status-dot" />
          Backend Connected
        </div>
      </aside>

      <main className="content">
        {page === "dashboard" && (
          <DashboardPage summary={summary} error={error} />
        )}

        {page === "machines" && !selectedMachineId && (
  <MachinesPage
    machines={machines}
    error={machinesError}
    onSelectMachine={setSelectedMachineId}
  />
)}

{page === "machines" && selectedMachineId && (
  <MachineDetailPage
    machine={machineDetail}
    error={machineDetailError}
    trends={machineTrends}
    trendsError={machineTrendsError}
    onBack={() => {
      setSelectedMachineId(null);
      setMachineDetail(null);
      setMachineTrends(null);
    }}
  />
)}
        {page === "alerts" && (
          <AlertsPage alerts={alerts} error={alertsError} />
        )}
      </main>
    </div>
  );
}

function DashboardPage({
  summary,
  error,
}: {
  summary: DashboardSummary | null;
  error: string;
}) {
  if (error) {
    return <div className="status-message">Error: {error}</div>;
  }

  if (!summary) {
    return <div className="status-message">Loading NEXUS ONE...</div>;
  }

  return (
    <>
      <header className="page-header">
        <div>
          <p className="eyebrow">Operations Overview</p>
          <h1>Dashboard</h1>
          <p className="subtitle">
            Real-time manufacturing intelligence across the enterprise.
          </p>
        </div>

        <div className="system-status">
          <span className="status-dot" />
          System Online
        </div>
      </header>

      <section className="grid">
        <MetricCard label="Factories" value={summary.factories} />
        <MetricCard
          label="Production Lines"
          value={summary.production_lines}
        />
        <MetricCard label="Machines" value={summary.machines} />
        <MetricCard label="Sensors" value={summary.sensors} />
        <MetricCard
          label="Sensor Readings"
          value={summary.sensor_readings.toLocaleString()}
        />
      </section>

      <section className="section">
        <h2>Fleet Health</h2>

        <div className="grid">
          <MetricCard label="Healthy" value={summary.healthy_machines} />
          <MetricCard label="Warning" value={summary.warning_machines} />
          <MetricCard label="Critical" value={summary.critical_machines} />
        </div>
      </section>

      <section className="section">
        <h2>Alert Overview</h2>

        <div className="grid">
          <MetricCard label="Active Alerts" value={summary.active_alerts} />
          <MetricCard label="Warnings" value={summary.warning_alerts} />
          <MetricCard
            label="Critical Alerts"
            value={summary.critical_alerts}
          />
          <MetricCard label="Resolved" value={summary.resolved_alerts} />
        </div>
      </section>
    </>
  );
}
function MachinesPage({
  machines,
  error,
  onSelectMachine,
}: {
  machines: MachineFleetItem[];
  error: string;
  onSelectMachine: (machineId: string) => void;
}) {
  if (error) {
    return <div className="status-message">Error: {error}</div>;
  }

  return (
    <>
      <header className="page-header">
        <div>
          <p className="eyebrow">Manufacturing Assets</p>
          <h1>Machine Fleet</h1>
          <p className="subtitle">
            Current health status across all production equipment.
          </p>
        </div>
      </header>

      <div className="machine-table-wrapper">
        <table className="machine-table">
          <thead>
            <tr>
              <th>Machine</th>
              <th>Serial Number</th>
              <th>Production Line</th>
              <th>Status</th>
              <th>Health</th>
            </tr>
          </thead>

          <tbody>
            {machines.map((machine) => (
              <tr
                key={machine.id}
                className="clickable-row"
                onClick={() => onSelectMachine(machine.id)}
>
                <td>{machine.name}</td>
                <td>{machine.serial_number}</td>
                <td>{machine.production_line}</td>
                <td>
                  <span
                    className={`health-badge ${machine.health_status.toLowerCase()}`}
                  >
                    {machine.health_status}
                  </span>
                </td>
                <td>{machine.health_score}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

function MachineDetailPage({
  machine,
  error,
  trends,
  trendsError,
  onBack,
}: {
  machine: MachineDetail | null;
  error: string;
  trends: MachineTrends | null;
  trendsError: string;
  onBack: () => void;
}) {
  if (error) {
    return <div className="status-message">Error: {error}</div>;
  }

  if (!machine) {
    return <div className="status-message">Loading machine details...</div>;
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
          <p className="subtitle">Serial: {machine.serial_number}</p>
        </div>

        <span
          className={`health-badge ${machine.health_status.toLowerCase()}`}
        >
          {machine.health_status}
        </span>
      </header>

      <section className="grid">
        <MetricCard label="Health Score" value={`${machine.health_score}%`} />
        <MetricCard
          label="Temperature"
          value={machine.temperature ?? "—"}
        />
        <MetricCard label="Pressure" value={machine.pressure ?? "—"} />
        <MetricCard
          label="Vibration"
          value={machine.vibration ?? "—"}
        />
        <MetricCard label="RPM" value={machine.rpm ?? "—"} />
        <MetricCard label="Energy" value={machine.energy ?? "—"} />
      </section>

      <section className="section">
        <h2>Warnings</h2>

        {machine.warnings.length === 0 ? (
          <p className="no-warnings">No active machine warnings.</p>
        ) : (
          <div className="warning-list">
            {machine.warnings.map((warning) => (
              <div className="warning-item" key={warning}>
                {warning}
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="section">
        <h2>Telemetry Trends</h2>

        {trendsError && (
          <p className="no-warnings">Error loading trends: {trendsError}</p>
        )}

        {!trends && !trendsError && (
          <p className="no-warnings">Loading telemetry trends...</p>
        )}

        {trends && (
          <div className="charts-grid">
            <TrendChart title="Temperature" data={trends.temperature} />
            <TrendChart title="Pressure" data={trends.pressure} />
            <TrendChart title="Vibration" data={trends.vibration} />
            <TrendChart title="RPM" data={trends.rpm} />
            <TrendChart title="Energy" data={trends.energy} />
          </div>
        )}
      </section>
    </>
  );
}

function TrendChart({
  title,
  data,
}: {
  title: string;
  data: TelemetryTrendPoint[];
}) {
  const chartData = data.map((point) => ({
    time: new Date(point.recorded_at).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    }),
    value: point.value,
  }));

  return (
    <article className="chart-card">
      <h3>{title}</h3>

      <div className="chart-container">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="time" />
            <YAxis />
            <Tooltip />
            <Line
              type="monotone"
              dataKey="value"
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </article>
  );
}

function MetricCard({
  label,
  value,
}: {
  label: string;
  value: string | number;
}) {
  return (
    <article className="card">
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  );
}

function AlertsPage({
  alerts,
  error,
}: {
  alerts: AlertItem[];
  error: string;
}) {
  if (error) {
    return <div className="status-message">Error: {error}</div>;
  }

  return (
    <>
      <header className="page-header">
        <div>
          <p className="eyebrow">Operational Events</p>
          <h1>Active Alerts</h1>
          <p className="subtitle">
            Current warning and critical conditions across the fleet.
          </p>
        </div>
      </header>

      <div className="alerts-list">
        {alerts.length === 0 ? (
          <p className="no-warnings">No active alerts.</p>
        ) : (
          alerts.map((alert) => (
            <article
              key={alert.id}
              className={`alert-card ${alert.severity.toLowerCase()}`}
            >
              <div>
                <div className="alert-header">
                  <span
                    className={`health-badge ${alert.severity.toLowerCase()}`}
                  >
                    {alert.severity}
                  </span>

                  <span className="alert-type">
                    {alert.alert_type.replaceAll("_", " ")}
                  </span>
                </div>

                <h3>{alert.machine_name}</h3>
                <p>{alert.message}</p>
              </div>

              <time>
                {new Date(alert.created_at).toLocaleString()}
              </time>
            </article>
          ))
        )}
      </div>
    </>
  );
}

export default App;
