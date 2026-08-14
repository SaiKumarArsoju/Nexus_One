import type {
  AlertItem,
  DashboardSummary,
  MachineDetail,
  MachineFleetItem,
  MachineTrends,
} from "../types/api";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

async function request<T>(
  url: string,
  options?: RequestInit,
): Promise<T> {
  const response = await fetch(
    `${API_BASE_URL}${url}`,
    options,
  );

  if (!response.ok) {
    throw new Error(
      `Request failed with status ${response.status}`,
    );
  }

  return response.json() as Promise<T>;
}

export function getDashboardSummary(): Promise<DashboardSummary> {
  return request<DashboardSummary>("/dashboard/summary");
}

export function getMachines(): Promise<MachineFleetItem[]> {
  return request<MachineFleetItem[]>("/machines");
}

export function getMachineDetail(
  machineId: string,
): Promise<MachineDetail> {
  return request<MachineDetail>(`/machines/${machineId}`);
}

export function getMachineTrends(
  machineId: string,
): Promise<MachineTrends> {
  return request<MachineTrends>(`/machines/${machineId}/trends`);
}

export function getAlerts(): Promise<AlertItem[]> {
  return request<AlertItem[]>("/alerts");
}

export function acknowledgeAlert(
  alertId: string,
): Promise<AlertItem> {
  return request<AlertItem>(
    `/alerts/${alertId}/acknowledge`,
    {
      method: "PATCH",
    },
  );
}

export function resolveAlert(
  alertId: string,
): Promise<AlertItem> {
  return request<AlertItem>(
    `/alerts/${alertId}/resolve`,
    {
      method: "PATCH",
    },
  );
}
