import { useEffect, useState } from "react";
import "./App.css";

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

function App() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [error, setError] = useState("");

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

  if (error) {
    return <div className="status-message">Error: {error}</div>;
  }

  if (!summary) {
    return <div className="status-message">Loading NEXUS ONE...</div>;
  }

  return (
    <main className="dashboard">
      <header className="dashboard-header">
        <div>
          <p className="eyebrow">Industrial Intelligence Platform</p>
          <h1>NEXUS ONE</h1>
          <p className="subtitle">
            Real-time manufacturing operations overview
          </p>
        </div>

        <div className="system-status">
          <span className="status-dot" />
          System Online
        </div>
      </header>

      <section className="grid">
        <article className="card">
          <span>Factories</span>
          <strong>{summary.factories}</strong>
        </article>

        <article className="card">
          <span>Production Lines</span>
          <strong>{summary.production_lines}</strong>
        </article>

        <article className="card">
          <span>Machines</span>
          <strong>{summary.machines}</strong>
        </article>

        <article className="card">
          <span>Sensors</span>
          <strong>{summary.sensors}</strong>
        </article>

        <article className="card wide">
          <span>Sensor Readings</span>
          <strong>{summary.sensor_readings.toLocaleString()}</strong>
        </article>
      </section>

      <section className="section">
        <h2>Fleet Health</h2>

        <div className="grid">
          <article className="card">
            <span>Healthy</span>
            <strong>{summary.healthy_machines}</strong>
          </article>

          <article className="card">
            <span>Warning</span>
            <strong>{summary.warning_machines}</strong>
          </article>

          <article className="card">
            <span>Critical</span>
            <strong>{summary.critical_machines}</strong>
          </article>
        </div>
      </section>

      <section className="section">
        <h2>Alert Overview</h2>

        <div className="grid">
          <article className="card">
            <span>Active Alerts</span>
            <strong>{summary.active_alerts}</strong>
          </article>

          <article className="card">
            <span>Warnings</span>
            <strong>{summary.warning_alerts}</strong>
          </article>

          <article className="card">
            <span>Critical Alerts</span>
            <strong>{summary.critical_alerts}</strong>
          </article>

          <article className="card">
            <span>Resolved</span>
            <strong>{summary.resolved_alerts}</strong>
          </article>
        </div>
      </section>
    </main>
  );
}

export default App;
