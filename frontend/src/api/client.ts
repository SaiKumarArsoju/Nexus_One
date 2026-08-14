import type {
  AlertItem,
  DashboardSummary,
  MachineDetail,
  MachineFleetItem,
  MachineTrends,
} from "../types/api";

const API_BASE_URL = "http://127.0.0.1:8000/api/v1";

async function request<T>(url: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${url}`);

  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
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
