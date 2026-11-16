import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { Icon, type IconName } from "./Icon";
import { cx } from "./ui";

type ToastTone = "info" | "success" | "error";

type Toast = {
  id: number;
  tone: ToastTone;
  title: string;
  message?: string;
};

type ToastContextValue = {
  push: (toast: Omit<Toast, "id">) => void;
};

const ToastContext = createContext<ToastContextValue>({ push: () => undefined });

const TOAST_ICONS: Record<ToastTone, IconName> = {
  info: "info",
  success: "check-circle",
  error: "alert-triangle",
};

let nextId = 1;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const dismiss = useCallback((id: number) => {
    setToasts((current) => current.filter((toast) => toast.id !== id));
  }, []);

  const push = useCallback(
    (toast: Omit<Toast, "id">) => {
      const id = nextId++;
      setToasts((current) => [...current, { ...toast, id }]);
      window.setTimeout(() => dismiss(id), 7000);
    },
    [dismiss],
  );

  const value = useMemo(() => ({ push }), [push]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div
        role="status"
        aria-live="polite"
        className="pointer-events-none fixed bottom-5 right-5 z-[60] flex w-80 flex-col gap-2"
      >
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className="pointer-events-auto flex animate-fade-up items-start gap-2.5 rounded-md border border-line bg-surface px-3.5 py-3 shadow-overlay"
          >
            <span
              className={cx(
                "mt-0.5",
                toast.tone === "error" && "text-danger",
                toast.tone === "success" && "text-success",
                toast.tone === "info" && "text-accent",
              )}
            >
              <Icon name={TOAST_ICONS[toast.tone]} className="h-4 w-4" />
            </span>
            <div className="min-w-0 flex-1">
              <div className="text-xs font-semibold text-ink">{toast.title}</div>
              {toast.message && (
                <div className="mt-0.5 break-words text-xs text-ink-muted">
                  {toast.message}
                </div>
              )}
            </div>
            <button
              type="button"
              onClick={() => dismiss(toast.id)}
              className="-m-1 rounded-sm p-1 text-ink-faint transition-colors hover:text-ink"
              aria-label="Dismiss notification"
            >
              <Icon name="close" className="h-3.5 w-3.5" />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  return useContext(ToastContext);
}
