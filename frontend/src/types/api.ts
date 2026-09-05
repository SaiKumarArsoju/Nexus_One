export type DashboardSummary = {
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

export type MachineFleetItem = {
  id: string;
  name: string;
  serial_number: string;
  production_line: string;
  health_status: string;
  health_score: number;
};

export type MachineDetail = {
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

export type TelemetryTrendPoint = {
  recorded_at: string;
  value: number;
};

export type MachineTrends = {
  machine_id: string;
  machine_name: string;
  temperature: TelemetryTrendPoint[];
  pressure: TelemetryTrendPoint[];
  vibration: TelemetryTrendPoint[];
  rpm: TelemetryTrendPoint[];
  energy: TelemetryTrendPoint[];
};

export type SensorDiscovery = {
  id: string;
  name: string;
  sensor_type: SensorType;
  unit: string;
  machine_id: string;
};

export type TelemetryAggregationBucket = "1m" | "5m" | "15m" | "1h";

export type TelemetryAggregateBucket = {
  bucket_start: string;
  average: number;
  minimum: number;
  maximum: number;
  count: number;
};

export type AlertSeverity = "WARNING" | "CRITICAL";

export type AlertStatus = "ACTIVE" | "ACKNOWLEDGED" | "RESOLVED";

export type SensorType =
  | "TEMPERATURE"
  | "PRESSURE"
  | "VIBRATION"
  | "RPM"
  | "ENERGY";

export type AlertThreshold = {
  sensor_type: SensorType;
  threshold_value: number;
  unit: string;
  severity: AlertSeverity;
  alert_type: string;
  updated_at: string;
};

export type AlertItem = {
  id: string;
  machine_id: string;
  machine_name: string;
  severity: AlertSeverity;
  status: AlertStatus;
  alert_type: string;
  message: string;
  created_at: string;
};

export type RealtimeEvent<TData> = {
  id: string;
  type: string;
  occurred_at: string;
  resource_id: string | null;
  data: TData;
};

export type TelemetryUpdatedEventData = {
  sensor_id: string;
  machine_id: string;
};

export type AlertChangedEventData = {
  alert_id: string;
  machine_id: string;
  status: AlertStatus;
};
