import { useCallback, useEffect, useRef } from "react";

export const DEFAULT_POLL_INTERVAL_MS = 5_000;

type CurrentExecutionCheck = () => boolean;
type PollingTask = (
  isCurrent: CurrentExecutionCheck,
) => Promise<void>;

type UsePollingOptions = {
  enabled?: boolean;
  immediate?: boolean;
  intervalMs?: number;
  pollingKey?: string;
};

const resolvedPromise = Promise.resolve();

export function usePolling(
  task: PollingTask,
  {
    enabled = true,
    immediate = true,
    intervalMs = DEFAULT_POLL_INTERVAL_MS,
    pollingKey,
  }: UsePollingOptions = {},
): () => Promise<void> {
  const taskRef = useRef(task);
  const executeRef = useRef<(forceRefresh: boolean) => Promise<void>>(
    () => resolvedPromise,
  );

  useEffect(() => {
    taskRef.current = task;
  }, [task]);

  useEffect(() => {
    if (!enabled) {
      executeRef.current = () => resolvedPromise;
      return;
    }

    let cancelled = false;
    let timeoutId: number | undefined;
    let inFlight: Promise<void> | null = null;
    let rerunRequested = false;

    const isCurrent = () => !cancelled;

    const scheduleNext = () => {
      if (cancelled) {
        return;
      }

      window.clearTimeout(timeoutId);
      timeoutId = window.setTimeout(() => {
        void execute(false);
      }, intervalMs);
    };

    const execute = async (forceRefresh: boolean): Promise<void> => {
      if (inFlight) {
        if (forceRefresh) {
          rerunRequested = true;
        }

        return inFlight;
      }

      if (
        !forceRefresh &&
        document.visibilityState !== "visible"
      ) {
        scheduleNext();
        return;
      }

      const run = async () => {
        do {
          rerunRequested = false;

          try {
            await taskRef.current(isCurrent);
          } catch {
            // Page loaders own their initial/background error presentation.
          }
        } while (
          rerunRequested &&
          !cancelled &&
          document.visibilityState === "visible"
        );
      };

      inFlight = run();

      try {
        await inFlight;
      } finally {
        inFlight = null;
        scheduleNext();
      }
    };

    executeRef.current = execute;

    const handleVisibilityChange = () => {
      if (document.visibilityState === "visible") {
        window.clearTimeout(timeoutId);
        void execute(true);
      }
    };

    document.addEventListener(
      "visibilitychange",
      handleVisibilityChange,
    );

    if (immediate && document.visibilityState === "visible") {
      void execute(false);
    } else {
      scheduleNext();
    }

    return () => {
      cancelled = true;
      rerunRequested = false;
      window.clearTimeout(timeoutId);
      document.removeEventListener(
        "visibilitychange",
        handleVisibilityChange,
      );

      if (executeRef.current === execute) {
        executeRef.current = () => resolvedPromise;
      }
    };
  }, [enabled, immediate, intervalMs, pollingKey]);

  return useCallback(
    () => executeRef.current(true),
    [],
  );
}
