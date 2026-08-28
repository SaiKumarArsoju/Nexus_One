import { useEffect, useState } from "react";
import "./App.css";
import DashboardPage from "./pages/DashboardPage";
import MachinesPage from "./pages/MachinesPage";
import MachineDetailRoute from "./pages/MachineDetailPage";
import AlertsPage from "./pages/AlertsPage";
import AlertHistoryPage from "./pages/AlertHistoryPage";
import AlertThresholdsPage from "./pages/AlertThresholdsPage";

import {
  getAlerts,
  getAlertHistory,
  getAlertThresholds,
  getDashboardSummary,
  getMachineDetail,
  getMachines,
  getMachineTrends,
  updateAlertThreshold,
} from "./api/client";

import {
  NavLink,
  Route,
  Routes,
  useNavigate,
} from "react-router-dom";

import type {
  AlertItem,
  AlertThreshold,
  DashboardSummary,
  MachineDetail,
  MachineFleetItem,
  MachineTrends,
  SensorType,
} from "./types/api";

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
  const [alertHistory, setAlertHistory] = useState<AlertItem[]>([]);
  const [alertHistoryError, setAlertHistoryError] = useState("");
  const [alertHistoryLoading, setAlertHistoryLoading] = useState(true);
  const [alertThresholds, setAlertThresholds] = useState<AlertThreshold[]>([]);
  const [alertThresholdsError, setAlertThresholdsError] = useState("");
  const [alertThresholdsLoading, setAlertThresholdsLoading] = useState(true);
  const [machineStatusShortcut, setMachineStatusShortcut] = useState("ALL");
  const [alertSeverityShortcut, setAlertSeverityShortcut] = useState("ALL");

function refreshAlerts() {
  getAlerts()
    .then(setAlerts)
    .catch((err: Error) => {
      setAlertsError(err.message);
    });
}

function refreshAlertHistory() {
  setAlertHistoryLoading(true);
  setAlertHistoryError("");

  getAlertHistory()
    .then(setAlertHistory)
    .catch((err: Error) => {
      setAlertHistoryError(err.message);
    })
    .finally(() => {
      setAlertHistoryLoading(false);
    });
}

function refreshAlertData() {
  refreshAlerts();
  refreshAlertHistory();
}

useEffect(() => {
  refreshAlertData();
}, []);

useEffect(() => {
  setAlertThresholdsLoading(true);
  setAlertThresholdsError("");

  getAlertThresholds()
    .then(setAlertThresholds)
    .catch((err: Error) => {
      setAlertThresholdsError(err.message);
    })
    .finally(() => {
      setAlertThresholdsLoading(false);
    });
}, []);

async function handleUpdateAlertThreshold(
  sensorType: SensorType,
  thresholdValue: number,
): Promise<AlertThreshold> {
  const updatedThreshold = await updateAlertThreshold(
    sensorType,
    thresholdValue,
  );

  setAlertThresholds((currentThresholds) =>
    currentThresholds.map((threshold) =>
      threshold.sensor_type === updatedThreshold.sensor_type
        ? updatedThreshold
        : threshold,
    ),
  );

  return updatedThreshold;
}

 useEffect(() => {
  if (!selectedMachineId) {
    return;
  }

  setMachineTrends(null);
  setMachineTrendsError("");

  getMachineTrends(selectedMachineId)
    .then(setMachineTrends)
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

  getMachineDetail(selectedMachineId)
    .then(setMachineDetail)
    .catch((err: Error) => {
      setMachineDetailError(err.message);
    });
}, [selectedMachineId]);

 useEffect(() => {
  getDashboardSummary()
    .then(setSummary)
    .catch((err: Error) => {
      setError(err.message);
    });
}, []);

 useEffect(() => {
  getMachines()
    .then(setMachines)
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
            end
            className={({ isActive }) =>
              isActive ? "nav-item active" : "nav-item"
            }
          >
            Active Alerts
          </NavLink>

          <NavLink
            to="/alerts/history"
            className={({ isActive }) =>
              isActive ? "nav-item active" : "nav-item"
            }
          >
            Alert History
          </NavLink>

          <NavLink
            to="/alert-thresholds"
            className={({ isActive }) =>
              isActive ? "nav-item active" : "nav-item"
            }
          >
            Alert Thresholds
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
                  alerts={alerts}
                  machines={machines}
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
                  onAlertMachineClick={(machineId) => {
                    navigate(`/machines/${machineId}`);
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
              path="/alerts/history"
              element={
                <AlertHistoryPage
                  alerts={alertHistory}
                  error={alertHistoryError}
                  loading={alertHistoryLoading}
                  onSelectMachine={(machineId) => {
                    navigate(`/machines/${machineId}`);
                  }}
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
                  onAlertsChanged={refreshAlertData}
                  onSelectMachine={(machineId) => {
                    navigate(`/machines/${machineId}`);
                  }}
                />
              }
            />

            <Route
              path="/alert-thresholds"
              element={
                <AlertThresholdsPage
                  thresholds={alertThresholds}
                  error={alertThresholdsError}
                  loading={alertThresholdsLoading}
                  onUpdateThreshold={handleUpdateAlertThreshold}
                />
              }
            />
          </Routes>
      </main>
    </div>
  );
}


export default App;
