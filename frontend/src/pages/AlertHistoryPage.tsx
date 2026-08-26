import { useState } from "react";
import { useSearchParams } from "react-router-dom";

import type {
  AlertItem,
  AlertSeverity,
  AlertStatus,
} from "../types/api";

type AlertHistoryPageProps = {
  alerts: AlertItem[];
  error: string;
  loading: boolean;
  onSelectMachine: (machineId: string) => void;
};

type StatusFilter = "ALL" | AlertStatus;
type SeverityFilter = "ALL" | AlertSeverity;

function AlertHistoryPage({
  alerts,
  error,
  loading,
  onSelectMachine,
}: AlertHistoryPageProps) {
  const [searchParams, setSearchParams] = useSearchParams();
  const [search, setSearch] = useState("");

  const statusFilter = (
    searchParams.get("status") ?? "ALL"
  ) as StatusFilter;
  const severityFilter = (
    searchParams.get("severity") ?? "ALL"
  ) as SeverityFilter;

  if (error) {
    return <div className="status-message">Error: {error}</div>;
  }

  if (loading) {
    return (
      <div className="status-message">
        Loading alert history...
      </div>
    );
  }

  const normalizedSearch = search.trim().toLowerCase();
  const filteredAlerts = alerts.filter((alert) => {
    const matchesSearch =
      alert.machine_name.toLowerCase().includes(normalizedSearch) ||
      alert.alert_type.toLowerCase().includes(normalizedSearch) ||
      alert.message.toLowerCase().includes(normalizedSearch);

    const matchesStatus =
      statusFilter === "ALL" || alert.status === statusFilter;
    const matchesSeverity =
      severityFilter === "ALL" ||
      alert.severity === severityFilter;

    return matchesSearch && matchesStatus && matchesSeverity;
  });

  function updateFilter(
    key: "status" | "severity",
    value: string,
  ) {
    const next = new URLSearchParams(searchParams);

    if (value === "ALL") {
      next.delete(key);
    } else {
      next.set(key, value);
    }

    setSearchParams(next);
  }

  function handleCardKeyDown(
    event: React.KeyboardEvent<HTMLElement>,
    machineId: string,
  ) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onSelectMachine(machineId);
    }
  }

  return (
    <>
      <header className="page-header">
        <div>
          <p className="eyebrow">Operational Audit Trail</p>
          <h1>Alert History</h1>
          <p className="subtitle">
            Review current and resolved operational incidents across the fleet.
          </p>
        </div>
      </header>

      <div className="filters-bar">
        <input
          className="search-input"
          type="search"
          aria-label="Search alert history"
          placeholder="Search machine, alert type, or message..."
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />

        <select
          className="filter-select"
          aria-label="Filter alert history by status"
          value={statusFilter}
          onChange={(event) =>
            updateFilter("status", event.target.value)
          }
        >
          <option value="ALL">All Statuses</option>
          <option value="ACTIVE">Active</option>
          <option value="ACKNOWLEDGED">Acknowledged</option>
          <option value="RESOLVED">Resolved</option>
        </select>

        <select
          className="filter-select"
          aria-label="Filter alert history by severity"
          value={severityFilter}
          onChange={(event) =>
            updateFilter("severity", event.target.value)
          }
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
          <p className="no-warnings">No alert history found.</p>
        ) : (
          filteredAlerts.map((alert) => (
            <article
              key={alert.id}
              className={`alert-card history-card ${alert.severity.toLowerCase()} status-${alert.status.toLowerCase()}`}
              role="link"
              tabIndex={0}
              aria-label={`View ${alert.machine_name} machine details`}
              onClick={() => onSelectMachine(alert.machine_id)}
              onKeyDown={(event) =>
                handleCardKeyDown(event, alert.machine_id)
              }
            >
              <div className="history-card-main">
                <div className="alert-header">
                  <span
                    className={`health-badge ${alert.severity.toLowerCase()}`}
                  >
                    {alert.severity}
                  </span>

                  <span
                    className={`alert-status ${alert.status.toLowerCase()}`}
                  >
                    {alert.status}
                  </span>

                  <span className="alert-type">
                    {alert.alert_type.replaceAll("_", " ")}
                  </span>
                </div>

                <h3>{alert.machine_name}</h3>
                <p>{alert.message}</p>
              </div>

              <div className="history-card-meta">
                <span>Created</span>
                <time dateTime={alert.created_at}>
                  {new Date(alert.created_at).toLocaleString()}
                </time>
              </div>
            </article>
          ))
        )}
      </div>
    </>
  );
}

export default AlertHistoryPage;
