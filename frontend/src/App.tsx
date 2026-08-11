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
  Cell,
  Pie,
  PieChart,
} from "recharts";

import {
  NavLink,
  Route,
  Routes,
  useNavigate,
  useParams,
  useSearchParams,
} from "react-router-dom";

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
  const navigate = useNavigate();

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
  const [machineStatusShortcut, setMachineStatusShortcut] = useState("ALL");
  const [alertSeverityShortcut, setAlertSeverityShortcut] = useState("ALL");

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
          <NavLink
            to="/"
            end
            className={({ isActive }) =>
              isActive ? "nav-item active" : "nav-item"
            }
          >
            Dashboard
          </NavLink>

          <NavLink
            to="/machines"
            className={({ isActive }) =>
              isActive ? "nav-item active" : "nav-item"
          }
          >
            Machines
          </NavLink>

          <NavLink
            to="/alerts"
            className={({ isActive }) =>
              isActive ? "nav-item active" : "nav-item"
            }
          >
            Alerts
          </NavLink>
        </nav>

        <div className="sidebar-status">
          <span className="status-dot" />
          Backend Connected
        </div>
      </aside>

      <main className="content">
          <Routes>
            <Route
              path="/"
              element={
                <DashboardPage
                  summary={summary}
                  error={error}
                  onMachinesShortcut={(status) => {
                    setMachineStatusShortcut(status);
                    navigate(`/machines?status=${status}`);
                  }}
                  onAlertsShortcut={(severity) => {
                    setAlertSeverityShortcut(severity);

                    navigate(
                      severity === "ALL"
                        ? "/alerts"
                        : `/alerts?severity=${severity}`,
                    );
                  }}
                />
              }
            />

            <Route
              path="/machines"
              element={
                <MachinesPage
                  machines={machines}
                  error={machinesError}
                  initialStatusFilter={machineStatusShortcut}
                  onSelectMachine={(machineId) => {
                    navigate(`/machines/${machineId}`);
                  }}
                />
              }
            />

            <Route
              path="/machines/:machineId"
              element={
                <MachineDetailRoute
                  machine={machineDetail}
                  error={machineDetailError}
                  trends={machineTrends}
                  trendsError={machineTrendsError}
                  setSelectedMachineId={setSelectedMachineId}
                />
              }
            />

            <Route
              path="/alerts"
              element={
                <AlertsPage
                  alerts={alerts}
                  error={alertsError}
                  initialSeverityFilter={alertSeverityShortcut}
                  onSelectMachine={(machineId) => {
                    navigate(`/machines/${machineId}`);
                  }}
                />
              }
            />
          </Routes>
      </main>
    </div>
  );
}

function DashboardPage({
  summary,
  error,
  onMachinesShortcut,
  onAlertsShortcut,
}: {
  summary: DashboardSummary | null;
  error: string;
  onMachinesShortcut: (status: string) => void;
  onAlertsShortcut: (severity: string) => void;
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

<div className="analytics-grid">
  <section className="section">
    <h2>Fleet Health Distribution</h2>

    <div className="fleet-health-panel">
      <div className="fleet-health-chart">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={[
                {
                  name: "Healthy",
                  value: summary.healthy_machines,
                },
                {
                  name: "Warning",
                  value: summary.warning_machines,
                },
                {
                  name: "Critical",
                  value: summary.critical_machines,
                },
              ]}
              dataKey="value"
              nameKey="name"
              innerRadius={72}
              outerRadius={108}
              paddingAngle={4}
            >
              <Cell fill="#22c55e" />
              <Cell fill="#f59e0b" />
              <Cell fill="#ef4444" />
            </Pie>

            <Tooltip />
          </PieChart>
        </ResponsiveContainer>
      </div>

      <div className="fleet-health-legend">
        <div className="legend-item">
          <span className="legend-dot healthy-dot" />
          <div>
            <span>Healthy</span>
            <strong>{summary.healthy_machines}</strong>
          </div>
        </div>

        <div className="legend-item">
          <span className="legend-dot warning-dot" />
          <div>
            <span>Warning</span>
            <strong>{summary.warning_machines}</strong>
          </div>
        </div>

        <div className="legend-item">
          <span className="legend-dot critical-dot" />
          <div>
            <span>Critical</span>
            <strong>{summary.critical_machines}</strong>
          </div>
        </div>
      </div>
    </div>
  </section>

  <section className="section">
    <h2>Alert Severity Distribution</h2>

    <div className="fleet-health-panel">
      <div className="fleet-health-chart">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={[
                {
                  name: "Warning",
                  value: summary.warning_alerts,
                },
                {
                  name: "Critical",
                  value: summary.critical_alerts,
                },
              ]}
              dataKey="value"
              nameKey="name"
              innerRadius={72}
              outerRadius={108}
              paddingAngle={4}
            >
              <Cell fill="#f59e0b" />
              <Cell fill="#ef4444" />
            </Pie>

            <Tooltip />
          </PieChart>
        </ResponsiveContainer>
      </div>

      <div className="fleet-health-legend">
        <div className="legend-item">
          <span className="legend-dot warning-dot" />
          <div>
            <span>Warning</span>
            <strong>{summary.warning_alerts}</strong>
          </div>
        </div>

        <div className="legend-item">
          <span className="legend-dot critical-dot" />
          <div>
            <span>Critical</span>
            <strong>{summary.critical_alerts}</strong>
          </div>
        </div>

        <div className="legend-item">
          <span className="legend-dot resolved-dot" />
          <div>
            <span>Total Active</span>
            <strong>{summary.active_alerts}</strong>
          </div>
        </div>
      </div>
    </div>
  </section>
</div>

<section className="section">
  <h2>Fleet Health</h2>

  <div className="grid">
    <MetricCard label="Healthy" value={summary.healthy_machines} />

    <MetricCard
      label="Warning"
      value={summary.warning_machines}
      onClick={() => onMachinesShortcut("WARNING")}
    />

    <MetricCard
      label="Critical"
      value={summary.critical_machines}
      onClick={() => onMachinesShortcut("CRITICAL")}
    />
  </div>
</section>
      <section className="section">
        <h2>Alert Overview</h2>

        <div className="grid">
          <MetricCard
            label="Active Alerts"
            value={summary.active_alerts}
            onClick={() => onAlertsShortcut("ALL")}
          />

          <MetricCard label="Warnings" value={summary.warning_alerts} />

          <MetricCard
            label="Critical Alerts"
            value={summary.critical_alerts}
            onClick={() => onAlertsShortcut("CRITICAL")}
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
  initialStatusFilter,
}: {
  machines: MachineFleetItem[];
  error: string;
  onSelectMachine: (machineId: string) => void;
  initialStatusFilter: string;
}) {

  const [search, setSearch] = useState("");
const [searchParams, setSearchParams] = useSearchParams();

const statusFilter =
  searchParams.get("status") ?? initialStatusFilter;

const productionLineFilter =
  searchParams.get("line") ?? "ALL";

const productionLines = Array.from(
  new Set(machines.map((machine) => machine.production_line)),
).sort();

  const filteredMachines = machines.filter((machine) => {
  const matchesSearch =
    machine.name.toLowerCase().includes(search.toLowerCase()) ||
    machine.serial_number.toLowerCase().includes(search.toLowerCase()) ||
    machine.production_line.toLowerCase().includes(search.toLowerCase());

  const matchesStatus =
    statusFilter === "ALL" || machine.health_status === statusFilter;

  const matchesProductionLine =
    productionLineFilter === "ALL" ||
    machine.production_line === productionLineFilter;

  return matchesSearch && matchesStatus && matchesProductionLine;
});

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

<div className="filters-bar">
  <input
    className="search-input"
    type="text"
    placeholder="Search machine, serial number, or production line..."
    value={search}
    onChange={(event) => setSearch(event.target.value)}
  />
<select
  className="filter-select"
  value={productionLineFilter}
  onChange={(event) => {
    const next = new URLSearchParams(searchParams);

    if (event.target.value === "ALL") {
      next.delete("line");
    } else {
      next.set("line", event.target.value);
    }

    setSearchParams(next);
  }}
>
  <option value="ALL">All Production Lines</option>

  {productionLines.map((productionLine) => (
    <option key={productionLine} value={productionLine}>
      {productionLine}
    </option>
  ))}
</select>
  <select
    className="filter-select"
    value={statusFilter}
     onChange={(event) => {
    const next = new URLSearchParams(searchParams);

    if (event.target.value === "ALL") {
      next.delete("status");
    } else {
      next.set("status", event.target.value);
    }

    setSearchParams(next);
  }}
  >
    <option value="ALL">All Statuses</option>
    <option value="HEALTHY">Healthy</option>
    <option value="WARNING">Warning</option>
    <option value="CRITICAL">Critical</option>
  </select>
</div>

<p className="results-count">
  Showing {filteredMachines.length} of {machines.length} machines
</p>

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
            {filteredMachines.map((machine) => (
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
function MachineDetailRoute({
  machine,
  error,
  trends,
  trendsError,
  setSelectedMachineId,
}: {
  machine: MachineDetail | null;
  error: string;
  trends: MachineTrends | null;
  trendsError: string;
  setSelectedMachineId: (machineId: string | null) => void;
}) {
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
  onClick,
}: {
  label: string;
  value: string | number;
  onClick?: () => void;
}) {
  return (
    <article
      className={onClick ? "card clickable-card" : "card"}
      onClick={onClick}
    >
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  );
}

function AlertsPage({
  alerts,
  error,
  onSelectMachine,
  initialSeverityFilter,
}: {
  alerts: AlertItem[];
  error: string;
  onSelectMachine: (machineId: string) => void;
  initialSeverityFilter: string;
}) {

  const [searchParams, setSearchParams] = useSearchParams();

  const [search, setSearch] = useState("");

  const severityFilter =
    searchParams.get("severity") ?? initialSeverityFilter;

  if (error) {
    return <div className="status-message">Error: {error}</div>;
  }

  const filteredAlerts = alerts.filter((alert) => {
    const matchesSearch =
      alert.machine_name.toLowerCase().includes(search.toLowerCase()) ||
      alert.alert_type.toLowerCase().includes(search.toLowerCase()) ||
      alert.message.toLowerCase().includes(search.toLowerCase());

    const matchesSeverity =
      severityFilter === "ALL" || alert.severity === severityFilter;

    return matchesSearch && matchesSeverity;
  });

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

<div className="filters-bar">
  <input
    className="search-input"
    type="text"
    placeholder="Search machine, alert type, or message..."
    value={search}
    onChange={(event) => setSearch(event.target.value)}
  />

  <select
    className="filter-select"
    value={severityFilter}
    onChange={(event) => {
      const next = new URLSearchParams(searchParams);

      if (event.target.value === "ALL") {
        next.delete("severity");
      } else {
        next.set("severity", event.target.value);
      }

      setSearchParams(next);
    }}
  >
    <option value="ALL">All Severities</option>
    <option value="WARNING">Warning</option>
    <option value="CRITICAL">Critical</option>
  </select>
</div>

<p className="results-count">
  Showing {filteredAlerts.length} of {alerts.length} alerts
</p>

      <div className="alerts-list">
        {filteredAlerts.length === 0 ? (
          <p className="no-warnings">No active alerts.</p>
        ) : (
          filteredAlerts.map((alert) => (
            <article
              key={alert.id}
              className={`alert-card ${alert.severity.toLowerCase()}`}
              onClick={() => onSelectMachine(alert.machine_id)}
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
