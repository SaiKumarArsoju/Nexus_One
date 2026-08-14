import { useEffect, useState } from "react";
import "./App.css";
import DashboardPage from "./pages/DashboardPage";
import MachinesPage from "./pages/MachinesPage";
import MachineDetailRoute from "./pages/MachineDetailPage";
import AlertsPage from "./pages/AlertsPage";

import {
  getAlerts,
  getDashboardSummary,
  getMachineDetail,
  getMachines,
  getMachineTrends,
} from "./api/client";

import {
  NavLink,
  Route,
  Routes,
  useNavigate,
} from "react-router-dom";

import type {
  AlertItem,
  DashboardSummary,
  MachineDetail,
  MachineFleetItem,
  MachineTrends,
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
  const [machineStatusShortcut, setMachineStatusShortcut] = useState("ALL");
  const [alertSeverityShortcut, setAlertSeverityShortcut] = useState("ALL");

useEffect(() => {
  getAlerts()
    .then(setAlerts)
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


export default App;
