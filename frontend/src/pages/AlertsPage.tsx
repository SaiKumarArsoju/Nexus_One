import { useState } from "react";
import { useSearchParams } from "react-router-dom";

import type { AlertItem } from "../types/api";

type AlertsPageProps = {
  alerts: AlertItem[];
  error: string;
  onSelectMachine: (machineId: string) => void;
  initialSeverityFilter: string;
};

function AlertsPage({
  alerts,
  error,
  onSelectMachine,
  initialSeverityFilter,
}: AlertsPageProps) {
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
      severityFilter === "ALL" ||
      alert.severity === severityFilter;

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

export default AlertsPage;
