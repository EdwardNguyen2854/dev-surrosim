import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { api, ApiError, type Job } from "./api";

export function useDebouncedValue<T>(value: T, delayMs = 150): T {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const handle = window.setTimeout(() => setDebounced(value), delayMs);
    return () => window.clearTimeout(handle);
  }, [value, delayMs]);

  return debounced;
}

export function useJob<T = unknown>(jobId: string | null) {
  return useQuery({
    queryKey: ["job", jobId],
    queryFn: () => api.job(jobId as string) as Promise<Job<T>>,
    enabled: Boolean(jobId),
    retry: (failureCount, error) =>
      !(error instanceof ApiError && error.status === 404) && failureCount < 2,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "succeeded" || status === "failed" ? false : 800;
    },
  });
}

export function useElapsed(
  startedUtc: string | null,
  finishedUtc: string | null,
): number {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (!startedUtc || finishedUtc) {
      return;
    }
    const handle = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(handle);
  }, [startedUtc, finishedUtc]);

  if (!startedUtc) {
    return 0;
  }
  const start = new Date(startedUtc).getTime();
  const end = finishedUtc ? new Date(finishedUtc).getTime() : now;
  return Math.max(0, (end - start) / 1000);
}
