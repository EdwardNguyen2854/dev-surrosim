import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { ApiError } from "../lib/api";
import { useJob } from "../lib/hooks";

export type JobKind = "fea_verify" | "field_predict" | "optimize";

const STORAGE_KEY = "surrosim.jobs.v1";

type JobSlots = Record<JobKind, string | null>;

const EMPTY_SLOTS: JobSlots = {
  fea_verify: null,
  field_predict: null,
  optimize: null,
};

function loadStoredSlots(): JobSlots {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return EMPTY_SLOTS;
    }
    const parsed = JSON.parse(raw) as Partial<Record<JobKind, unknown>>;
    const slots = { ...EMPTY_SLOTS };
    for (const kind of Object.keys(EMPTY_SLOTS) as JobKind[]) {
      const value = parsed[kind];
      slots[kind] = typeof value === "string" && value ? value : null;
    }
    return slots;
  } catch {
    return EMPTY_SLOTS;
  }
}

type JobsContextValue = {
  slots: JobSlots;
  setSlot: (kind: JobKind, jobId: string | null) => void;
};

const JobsContext = createContext<JobsContextValue | null>(null);

export function JobsProvider({ children }: { children: ReactNode }) {
  const [slots, setSlots] = useState<JobSlots>(loadStoredSlots);

  useEffect(() => {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(slots));
  }, [slots]);

  const setSlot = useCallback((kind: JobKind, jobId: string | null) => {
    setSlots((current) =>
      current[kind] === jobId ? current : { ...current, [kind]: jobId },
    );
  }, []);

  const value = useMemo<JobsContextValue>(
    () => ({ slots, setSlot }),
    [slots, setSlot],
  );

  return <JobsContext.Provider value={value}>{children}</JobsContext.Provider>;
}

function useJobs(): JobsContextValue {
  const context = useContext(JobsContext);
  if (!context) {
    throw new Error("useJobs must be used inside JobsProvider");
  }
  return context;
}

export function useJobSlot<T = unknown>(kind: JobKind) {
  const { slots, setSlot } = useJobs();
  const jobId = slots[kind];
  const job = useJob<T>(jobId);
  const missing = job.error instanceof ApiError && job.error.status === 404;

  useEffect(() => {
    if (missing) {
      setSlot(kind, null);
    }
  }, [missing, kind, setSlot]);

  const setJobId = useCallback(
    (next: string | null) => setSlot(kind, next),
    [kind, setSlot],
  );

  return { jobId, job, setJobId };
}
