import {
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import {
  NavLink,
  Route,
  Routes,
  matchPath,
  useLocation,
  useNavigate,
} from "react-router-dom";

import "./App.css";
import {
  getAlertHistory,
  getAlerts,
  getAlertThresholds,
  getDashboardSummary,
  getMachineDetail,
  getMachines,
  getMachineTrends,
  updateAlertThreshold,
} from "./api/client";
import { usePolling } from "./hooks/usePolling";
import {
  useRealtimeEvents,
} from "./hooks/useRealtimeEvents";
import AlertHistoryPage from "./pages/AlertHistoryPage";
import AlertsPage from "./pages/AlertsPage";
import AlertThresholdsPage from "./pages/AlertThresholdsPage";
import DashboardPage from "./pages/DashboardPage";
import MachineDetailRoute from "./pages/MachineDetailPage";
import MachinesPage from "./pages/MachinesPage";

import type {
  AlertChangedEventData,
  AlertItem,
  AlertThreshold,
  DashboardSummary,
  MachineDetail,
  MachineFleetItem,
  MachineTrends,
  SensorType,
  TelemetryUpdatedEventData,
} from "./types/api";

type CurrentExecutionCheck = () => boolean;
type ForcedRefresh = () => Promise<void>;

const isAlwaysCurrent = () => true;
const REALTIME_REFRESH_DELAY_MS = 200;
const REALTIME_STATUS_LABELS = {
  connecting: "Realtime Connecting",
  connected: "Realtime Connected",
  reconnecting: "Realtime Reconnecting",
} as const;

function errorMessage(error: unknown): string {
  return error instanceof Error
    ? error.message
    : "An unexpected request error occurred.";
}

function App() {
  const navigate = useNavigate();
  const { pathname } = useLocation();

  const [summary, setSummary] = useState<DashboardSummary | null>(
    null,
  );
  const [error, setError] = useState("");
  const [machines, setMachines] = useState<MachineFleetItem[]>([]);
  const [machinesError, setMachinesError] = useState("");
  const [selectedMachineId, setSelectedMachineId] = useState<
    string | null
  >(null);
  const [machineDetail, setMachineDetail] =
    useState<MachineDetail | null>(null);
  const [machineDetailError, setMachineDetailError] =
    useState("");
  const [machineTrends, setMachineTrends] =
    useState<MachineTrends | null>(null);
  const [machineTrendsError, setMachineTrendsError] =
    useState("");
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [alertsError, setAlertsError] = useState("");
  const [alertHistory, setAlertHistory] = useState<AlertItem[]>(
    [],
  );
  const [alertHistoryError, setAlertHistoryError] = useState("");
  const [alertHistoryLoading, setAlertHistoryLoading] =
    useState(true);
  const [alertThresholds, setAlertThresholds] = useState<
    AlertThreshold[]
  >([]);
  const [alertThresholdsError, setAlertThresholdsError] =
    useState("");
  const [alertThresholdsLoading, setAlertThresholdsLoading] =
    useState(true);
  const [machineStatusShortcut, setMachineStatusShortcut] =
    useState("ALL");
  const [alertSeverityShortcut, setAlertSeverityShortcut] =
    useState("ALL");

  const summaryLoadedRef = useRef(false);
  const machinesLoadedRef = useRef(false);
  const alertsLoadedRef = useRef(false);
  const alertHistoryLoadedRef = useRef(false);
  const machineDetailLoadedRef = useRef(false);
  const machineTrendsLoadedRef = useRef(false);
  const realtimeRefreshTimersRef = useRef(
    new Map<string, number>(),
  );

  const scheduleRealtimeRefresh = useCallback(
    (domain: string, refresh: ForcedRefresh) => {
      if (
        document.visibilityState !== "visible" ||
        realtimeRefreshTimersRef.current.has(domain)
      ) {
        return;
      }

      const timeoutId = window.setTimeout(() => {
        realtimeRefreshTimersRef.current.delete(domain);
        void refresh();
      }, REALTIME_REFRESH_DELAY_MS);

      realtimeRefreshTimersRef.current.set(domain, timeoutId);
    },
    [],
  );

  useEffect(
    () => () => {
      for (const timeoutId of realtimeRefreshTimersRef.current.values()) {
        window.clearTimeout(timeoutId);
      }

      realtimeRefreshTimersRef.current.clear();
    },
    [],
  );

  const refreshSummary = useCallback(
    async (isCurrent: CurrentExecutionCheck) => {
      try {
        const nextSummary = await getDashboardSummary();

        if (isCurrent()) {
          setSummary(nextSummary);
          setError("");
          summaryLoadedRef.current = true;
        }
      } catch (requestError) {
        if (isCurrent() && !summaryLoadedRef.current) {
          setError(errorMessage(requestError));
        }
      }
    },
    [],
  );

  const refreshMachines = useCallback(
    async (isCurrent: CurrentExecutionCheck) => {
      try {
        const nextMachines = await getMachines();

        if (isCurrent()) {
          setMachines(nextMachines);
          setMachinesError("");
          machinesLoadedRef.current = true;
        }
      } catch (requestError) {
        if (isCurrent() && !machinesLoadedRef.current) {
          setMachinesError(errorMessage(requestError));
        }
      }
    },
    [],
  );

  const refreshAlerts = useCallback(
    async (isCurrent: CurrentExecutionCheck) => {
      try {
        const nextAlerts = await getAlerts();

        if (isCurrent()) {
          setAlerts(nextAlerts);
          setAlertsError("");
          alertsLoadedRef.current = true;
        }
      } catch (requestError) {
        if (isCurrent() && !alertsLoadedRef.current) {
          setAlertsError(errorMessage(requestError));
        }
      }
    },
    [],
  );

  const refreshAlertHistory = useCallback(
    async (isCurrent: CurrentExecutionCheck) => {
      const isInitialLoad = !alertHistoryLoadedRef.current;

      if (isInitialLoad && isCurrent()) {
        setAlertHistoryLoading(true);
        setAlertHistoryError("");
      }

      try {
        const nextHistory = await getAlertHistory();

        if (isCurrent()) {
          setAlertHistory(nextHistory);
          setAlertHistoryError("");
          alertHistoryLoadedRef.current = true;
        }
      } catch (requestError) {
        if (isCurrent() && !alertHistoryLoadedRef.current) {
          setAlertHistoryError(errorMessage(requestError));
        }
      } finally {
        if (isCurrent() && isInitialLoad) {
          setAlertHistoryLoading(false);
        }
      }
    },
    [],
  );

  const refreshDashboard = useCallback(
    async (isCurrent: CurrentExecutionCheck) => {
      await Promise.all([
        refreshSummary(isCurrent),
        refreshMachines(isCurrent),
        refreshAlerts(isCurrent),
      ]);
    },
    [refreshAlerts, refreshMachines, refreshSummary],
  );

  const refreshMachineData = useCallback(
    async (isCurrent: CurrentExecutionCheck) => {
      if (!selectedMachineId) {
        return;
      }

      const machineId = selectedMachineId;
      const [detailResult, trendsResult] =
        await Promise.allSettled([
          getMachineDetail(machineId),
          getMachineTrends(machineId),
        ]);

      if (!isCurrent()) {
        return;
      }

      if (detailResult.status === "fulfilled") {
        setMachineDetail(detailResult.value);
        setMachineDetailError("");
        machineDetailLoadedRef.current = true;
      } else if (!machineDetailLoadedRef.current) {
        setMachineDetailError(
          errorMessage(detailResult.reason),
        );
      }

      if (trendsResult.status === "fulfilled") {
        setMachineTrends(trendsResult.value);
        setMachineTrendsError("");
        machineTrendsLoadedRef.current = true;
      } else if (!machineTrendsLoadedRef.current) {
        setMachineTrendsError(
          errorMessage(trendsResult.reason),
        );
      }
    },
    [selectedMachineId],
  );

  useEffect(() => {
    if (!selectedMachineId) {
      return;
    }

    machineDetailLoadedRef.current = false;
    machineTrendsLoadedRef.current = false;
    setMachineDetail(null);
    setMachineDetailError("");
    setMachineTrends(null);
    setMachineTrendsError("");
  }, [selectedMachineId]);

  useEffect(() => {
    setAlertThresholdsLoading(true);
    setAlertThresholdsError("");

    getAlertThresholds()
      .then(setAlertThresholds)
      .catch((requestError: Error) => {
        setAlertThresholdsError(requestError.message);
      })
      .finally(() => {
        setAlertThresholdsLoading(false);
      });
  }, []);

  const refreshDashboardNow = usePolling(refreshDashboard, {
    enabled: pathname === "/",
    pollingKey: pathname,
  });

  const refreshMachinesNow = usePolling(refreshMachines, {
    enabled: pathname === "/machines",
    pollingKey: pathname,
  });

  const refreshMachineDataNow = usePolling(refreshMachineData, {
    enabled:
      pathname.startsWith("/machines/") &&
      selectedMachineId !== null,
    pollingKey: selectedMachineId ?? pathname,
  });

  const refreshActiveAlertsNow = usePolling(refreshAlerts, {
    enabled: pathname === "/alerts",
    pollingKey: pathname,
  });

  const refreshAlertHistoryNow = usePolling(refreshAlertHistory, {
    enabled: pathname === "/alerts/history",
    pollingKey: pathname,
  });

  const routeMachineId =
    matchPath("/machines/:machineId", pathname)?.params
      .machineId ?? null;

  const handleTelemetryUpdated = useCallback(
    (data: TelemetryUpdatedEventData) => {
      if (pathname === "/") {
        scheduleRealtimeRefresh(
          "dashboard",
          refreshDashboardNow,
        );
      } else if (pathname === "/machines") {
        scheduleRealtimeRefresh("machines", refreshMachinesNow);
      } else if (
        routeMachineId !== null &&
        selectedMachineId === routeMachineId &&
        data.machine_id === routeMachineId
      ) {
        scheduleRealtimeRefresh(
          `machine:${routeMachineId}`,
          refreshMachineDataNow,
        );
      }
    },
    [
      pathname,
      refreshDashboardNow,
      refreshMachineDataNow,
      refreshMachinesNow,
      routeMachineId,
      scheduleRealtimeRefresh,
      selectedMachineId,
    ],
  );

  const handleAlertRealtimeEvent = useCallback(
    (data: AlertChangedEventData) => {
      if (pathname === "/") {
        scheduleRealtimeRefresh(
          "dashboard",
          refreshDashboardNow,
        );
      } else if (pathname === "/machines") {
        scheduleRealtimeRefresh("machines", refreshMachinesNow);
      } else if (
        routeMachineId !== null &&
        selectedMachineId === routeMachineId &&
        data.machine_id === routeMachineId
      ) {
        scheduleRealtimeRefresh(
          `machine:${routeMachineId}`,
          refreshMachineDataNow,
        );
      } else if (pathname === "/alerts") {
        scheduleRealtimeRefresh(
          "active-alerts",
          refreshActiveAlertsNow,
        );
      } else if (pathname === "/alerts/history") {
        scheduleRealtimeRefresh(
          "alert-history",
          refreshAlertHistoryNow,
        );
      }
    },
    [
      pathname,
      refreshActiveAlertsNow,
      refreshAlertHistoryNow,
      refreshDashboardNow,
      refreshMachineDataNow,
      refreshMachinesNow,
      routeMachineId,
      scheduleRealtimeRefresh,
      selectedMachineId,
    ],
  );

  const realtimeConnectionState = useRealtimeEvents({
    onTelemetryUpdated: handleTelemetryUpdated,
    onAlertCreated: handleAlertRealtimeEvent,
    onAlertUpdated: handleAlertRealtimeEvent,
  });

  const handleAlertsChanged = useCallback(async () => {
    await Promise.all([
      refreshActiveAlertsNow(),
      refreshAlertHistory(isAlwaysCurrent),
    ]);
  }, [refreshActiveAlertsNow, refreshAlertHistory]);

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
          <span
            className={`status-dot ${realtimeConnectionState}`}
          />
          {REALTIME_STATUS_LABELS[realtimeConnectionState]}
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
                onAlertsChanged={handleAlertsChanged}
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
