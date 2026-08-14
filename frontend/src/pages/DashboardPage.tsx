import {
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";

import MetricCard from "../components/MetricCard";

import type {
  AlertItem,
  DashboardSummary,
  MachineFleetItem,
} from "../types/api";

type DashboardPageProps = {
  summary: DashboardSummary | null;
  error: string;
  onMachinesShortcut: (status: string) => void;
  onAlertsShortcut: (severity: string) => void;
  alerts: AlertItem[];
  onAlertMachineClick: (machineId: string) => void;
  machines: MachineFleetItem[];
};

function DashboardPage({
  summary,
  error,
  onMachinesShortcut,
  onAlertsShortcut,
  alerts,
  onAlertMachineClick,
  machines,
}: DashboardPageProps) {
  if (error) {
    return <div className="status-message">Error: {error}</div>;
  }

  if (!summary) {
    return <div className="status-message">Loading NEXUS ONE...</div>;
  }

  const recentAlerts = [...alerts]
    .sort(
      (a, b) =>
        new Date(b.created_at).getTime() -
        new Date(a.created_at).getTime(),
    )
    .slice(0, 6);

  const topRiskMachines = [...machines]
    .sort((a, b) => a.health_score - b.health_score)
    .slice(0, 5);

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
          <MetricCard
            label="Healthy"
            value={summary.healthy_machines}
          />

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

          <MetricCard
            label="Warnings"
            value={summary.warning_alerts}
          />

          <MetricCard
            label="Critical Alerts"
            value={summary.critical_alerts}
            onClick={() => onAlertsShortcut("CRITICAL")}
          />

          <MetricCard
            label="Resolved"
            value={summary.resolved_alerts}
          />
        </div>
      </section>

      <section className="section">
        <div className="section-heading-row">
          <div>
            <h2>Recent Active Alerts</h2>
            <p>Latest operational conditions requiring attention.</p>
          </div>

          <button
            className="view-all-button"
            onClick={() => onAlertsShortcut("ALL")}
          >
            View All Alerts
          </button>
        </div>

        <div className="recent-alerts">
          {recentAlerts.length === 0 ? (
            <p className="no-warnings">No active alerts.</p>
          ) : (
            recentAlerts.map((alert) => (
              <article
                className="recent-alert-row"
                key={alert.id}
                onClick={() =>
                  onAlertMachineClick(alert.machine_id)
                }
              >
                <div className="recent-alert-main">
                  <span
                    className={`health-badge ${alert.severity.toLowerCase()}`}
                  >
                    {alert.severity}
                  </span>

                  <div>
                    <strong>{alert.machine_name}</strong>
                    <p>{alert.message}</p>
                  </div>
                </div>

                <div className="recent-alert-meta">
                  <span>
                    {alert.alert_type.replaceAll("_", " ")}
                  </span>

                  <time>
                    {new Date(alert.created_at).toLocaleString()}
                  </time>
                </div>
              </article>
            ))
          )}
        </div>
      </section>

      <section className="section">
        <div className="section-heading-row">
          <div>
            <h2>Top Risk Machines</h2>
            <p>Machines with the lowest current health scores.</p>
          </div>

          <button
            className="view-all-button"
            onClick={() => onMachinesShortcut("ALL")}
          >
            View Machine Fleet
          </button>
        </div>

        <div className="risk-machines-grid">
          {topRiskMachines.map((machine) => (
            <article
              className="risk-machine-card"
              key={machine.id}
              onClick={() =>
                onAlertMachineClick(machine.id)
              }
            >
              <div>
                <span
                  className={`health-badge ${machine.health_status.toLowerCase()}`}
                >
                  {machine.health_status}
                </span>

                <h3>{machine.name}</h3>
                <p>{machine.production_line}</p>
              </div>

              <div className="risk-score">
                <span>Health</span>
                <strong>{machine.health_score}%</strong>
              </div>
            </article>
          ))}
        </div>
      </section>
    </>
  );
}

export default DashboardPage;
