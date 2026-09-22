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

export type HealthScoreWindow = "1h" | "6h" | "24h" | "7d";
export type HealthBand = "HEALTHY" | "WATCH" | "ATTENTION" | "INSUFFICIENT_DATA";
export type HealthConfidence = "NONE" | "LOW" | "MEDIUM" | "HIGH";
export type FeatureCoverageStatus = "NO_DATA" | "SPARSE" | "SUFFICIENT";

export type SensorHealthPenalty = {
  threshold_proximity: number;
  mean_level: number;
  exceedance: number;
  trend: number;
  variability: number;
};

export type SensorHealthScore = {
  sensor_id: string;
  sensor_name: string;
  sensor_type: SensorType;
  unit: string;
  health_score: number | null;
  health_band: HealthBand;
  confidence: HealthConfidence;
  threshold_value: number;
  component_penalties: SensorHealthPenalty;
  reasons: string[];
  coverage_status: FeatureCoverageStatus;
};

export type MachineHealthScore = {
  indicator_type: string;
  feature_version: string;
  scoring_version: string;
  machine_id: string;
  window: HealthScoreWindow;
  window_start: string;
  window_end: string;
  health_score: number | null;
  health_band: HealthBand;
  confidence: HealthConfidence;
  scored_sensor_count: number;
  total_sensor_count: number;
  most_concerning_sensor_id: string | null;
  lowest_sensor_score: number | null;
  sensor_scores: SensorHealthScore[];
  reasons: string[];
};

export type MaintenancePriority =
  | "NONE"
  | "LOW"
  | "MEDIUM"
  | "HIGH"
  | "CRITICAL"
  | "INSUFFICIENT_DATA";

export type MaintenanceEvidenceType =
  | "CRITICAL_ALERT"
  | "WARNING_ALERT"
  | "LOW_HEALTH_SCORE"
  | "CONCERNING_SENSOR"
  | "THRESHOLD_EXCEEDANCE"
  | "LOW_CONFIDENCE"
  | "MISSING_TELEMETRY";

export type RecommendedMaintenanceAction =
  | "CONTINUE_MONITORING"
  | "REVIEW_OPERATING_CONDITIONS"
  | "INSPECT_MACHINE"
  | "INSPECT_SENSOR_OR_COMPONENT"
  | "SCHEDULE_MAINTENANCE_REVIEW"
  | "IMMEDIATE_OPERATIONAL_REVIEW"
  | "VERIFY_TELEMETRY";

export type MaintenanceEvidence = {
  type: MaintenanceEvidenceType;
  message: string;
  sensor_id: string | null;
  sensor_name: string | null;
  alert_id: string | null;
  severity: AlertSeverity | null;
};

export type MachineMaintenanceAssessment = {
  indicator_type: string;
  feature_version: string;
  scoring_version: string;
  maintenance_policy_version: string;
  machine_id: string;
  window: HealthScoreWindow;
  window_start: string;
  window_end: string;
  health_score: number | null;
  health_band: HealthBand;
  confidence: HealthConfidence;
  maintenance_priority: MaintenancePriority;
  unresolved_alert_count: number;
  critical_alert_count: number;
  warning_alert_count: number;
  most_concerning_sensor_id: string | null;
  most_concerning_sensor_name: string | null;
  evidence: MaintenanceEvidence[];
  recommended_actions: RecommendedMaintenanceAction[];
  reasons: string[];
};
