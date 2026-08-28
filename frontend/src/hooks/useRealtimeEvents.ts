import { useEffect, useRef, useState } from "react";

import { buildApiUrl } from "../api/client";

import type {
  AlertChangedEventData,
  AlertStatus,
  RealtimeEvent,
  TelemetryUpdatedEventData,
} from "../types/api";

export type RealtimeConnectionState =
  | "connecting"
  | "connected"
  | "reconnecting";

type RealtimeEventHandlers = {
  onReconnect: () => void;
  onTelemetryUpdated: (data: TelemetryUpdatedEventData) => void;
  onAlertCreated: (data: AlertChangedEventData) => void;
  onAlertUpdated: (data: AlertChangedEventData) => void;
};

const ALERT_STATUSES: ReadonlySet<string> = new Set([
  "ACTIVE",
  "ACKNOWLEDGED",
  "RESOLVED",
]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return (
    typeof value === "object" &&
    value !== null &&
    !Array.isArray(value)
  );
}

function parseEventData(
  event: Event,
  expectedType: string,
): RealtimeEvent<Record<string, unknown>> | null {
  if (!(event instanceof MessageEvent)) {
    return null;
  }

  try {
    const parsed: unknown = JSON.parse(String(event.data));

    if (
      !isRecord(parsed) ||
      parsed.type !== expectedType ||
      !isRecord(parsed.data) ||
      typeof parsed.id !== "string" ||
      typeof parsed.occurred_at !== "string" ||
      (parsed.resource_id !== null &&
        typeof parsed.resource_id !== "string")
    ) {
      return null;
    }

    return {
      id: parsed.id,
      type: parsed.type,
      occurred_at: parsed.occurred_at,
      resource_id: parsed.resource_id,
      data: parsed.data,
    };
  } catch {
    return null;
  }
}

function parseTelemetryEvent(
  event: Event,
): TelemetryUpdatedEventData | null {
  const parsed = parseEventData(event, "telemetry.updated");

  if (
    !parsed ||
    typeof parsed.data.sensor_id !== "string" ||
    typeof parsed.data.machine_id !== "string"
  ) {
    return null;
  }

  return {
    sensor_id: parsed.data.sensor_id,
    machine_id: parsed.data.machine_id,
  };
}

function parseAlertEvent(
  event: Event,
  expectedType: "alert.created" | "alert.updated",
): AlertChangedEventData | null {
  const parsed = parseEventData(event, expectedType);

  if (
    !parsed ||
    typeof parsed.data.alert_id !== "string" ||
    typeof parsed.data.machine_id !== "string" ||
    typeof parsed.data.status !== "string" ||
    !ALERT_STATUSES.has(parsed.data.status)
  ) {
    return null;
  }

  return {
    alert_id: parsed.data.alert_id,
    machine_id: parsed.data.machine_id,
    status: parsed.data.status as AlertStatus,
  };
}

export function useRealtimeEvents(
  handlers: RealtimeEventHandlers,
): RealtimeConnectionState {
  const handlersRef = useRef(handlers);
  const hasConnectedOnceRef = useRef(false);
  const wasDisconnectedRef = useRef(false);
  const [connectionState, setConnectionState] =
    useState<RealtimeConnectionState>("connecting");

  useEffect(() => {
    handlersRef.current = handlers;
  }, [handlers]);

  useEffect(() => {
    const eventSource = new EventSource(
      buildApiUrl("/events/stream"),
    );

    setConnectionState("connecting");

    const handleOpen = () => {
      const shouldReconcile =
        hasConnectedOnceRef.current &&
        wasDisconnectedRef.current;

      hasConnectedOnceRef.current = true;
      wasDisconnectedRef.current = false;
      setConnectionState("connected");

      if (shouldReconcile) {
        handlersRef.current.onReconnect();
      }
    };

    const handleError = () => {
      if (hasConnectedOnceRef.current) {
        wasDisconnectedRef.current = true;
      }

      setConnectionState("reconnecting");
    };

    const handleConnected = () => {
      setConnectionState("connected");
    };

    const handleTelemetryUpdated = (event: Event) => {
      const data = parseTelemetryEvent(event);

      if (data) {
        handlersRef.current.onTelemetryUpdated(data);
      }
    };

    const handleAlertCreated = (event: Event) => {
      const data = parseAlertEvent(event, "alert.created");

      if (data) {
        handlersRef.current.onAlertCreated(data);
      }
    };

    const handleAlertUpdated = (event: Event) => {
      const data = parseAlertEvent(event, "alert.updated");

      if (data) {
        handlersRef.current.onAlertUpdated(data);
      }
    };

    eventSource.addEventListener("open", handleOpen);
    eventSource.addEventListener("error", handleError);
    eventSource.addEventListener(
      "system.connected",
      handleConnected,
    );
    eventSource.addEventListener(
      "telemetry.updated",
      handleTelemetryUpdated,
    );
    eventSource.addEventListener(
      "alert.created",
      handleAlertCreated,
    );
    eventSource.addEventListener(
      "alert.updated",
      handleAlertUpdated,
    );

    return () => {
      eventSource.removeEventListener("open", handleOpen);
      eventSource.removeEventListener("error", handleError);
      eventSource.removeEventListener(
        "system.connected",
        handleConnected,
      );
      eventSource.removeEventListener(
        "telemetry.updated",
        handleTelemetryUpdated,
      );
      eventSource.removeEventListener(
        "alert.created",
        handleAlertCreated,
      );
      eventSource.removeEventListener(
        "alert.updated",
        handleAlertUpdated,
      );
      eventSource.close();
    };
  }, []);

  return connectionState;
}
