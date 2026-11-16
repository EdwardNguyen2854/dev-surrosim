import {
  createContext, useCallback, useContext, useLayoutEffect, useRef, useState,
  type ReactNode,
} from "react";

import { applyTheme, savePreferences, type Preferences } from "../lib/preferences";

type SaveStatus = "idle" | "saving" | "saved" | "failed";
type PreferencesContextValue = {
  preferences: Preferences;
  status: SaveStatus;
  appearanceError: boolean;
  canUndo: boolean;
  update: (patch: Partial<Preferences>) => void;
  undo: () => void;
  retry: () => void;
};
const PreferencesContext = createContext<PreferencesContextValue | null>(null);

export function PreferencesProvider({
  initial, loadFailed, children,
}: {
  initial: Preferences;
  loadFailed: boolean;
  children: ReactNode;
}) {
  const [preferences, setPreferences] = useState(initial);
  const [status, setStatus] = useState<SaveStatus>(loadFailed ? "failed" : "idle");
  const [appearanceError, setAppearanceError] = useState(false);
  const [canUndo, setCanUndo] = useState(false);
  const current = useRef(initial);
  const previous = useRef<Preferences | null>(null);
  const revision = useRef(0);
  const writes = useRef(Promise.resolve());

  useLayoutEffect(() => {
    let active = true;
    void applyTheme(preferences.theme).then(
      () => { if (active) setAppearanceError(false); },
      () => { if (active) setAppearanceError(true); },
    );
    return () => { active = false; };
  }, [preferences.theme]);

  const persist = useCallback((next: Preferences) => {
    const version = ++revision.current;
    setStatus("saving");
    // Serialize rapid changes so an older save cannot overwrite the newest one.
    writes.current = writes.current.then(() => savePreferences(next)).then(
      () => { if (revision.current === version) setStatus("saved"); },
      () => { if (revision.current === version) setStatus("failed"); },
    );
  }, []);

  const update = useCallback((patch: Partial<Preferences>) => {
    const next = { ...current.current, ...patch };
    if (next.theme === current.current.theme &&
      next.sidebarCollapsed === current.current.sidebarCollapsed) return;
    previous.current = current.current;
    current.current = next;
    setCanUndo(true);
    setPreferences(next);
    persist(next);
  }, [persist]);

  const undo = useCallback(() => {
    if (!previous.current) return;
    const next = previous.current;
    previous.current = null;
    current.current = next;
    setCanUndo(false);
    setPreferences(next);
    persist(next);
  }, [persist]);

  const retry = useCallback(() => {
    persist(current.current);
    void applyTheme(current.current.theme).then(
      () => setAppearanceError(false),
      () => setAppearanceError(true),
    );
  }, [persist]);

  return (
    <PreferencesContext.Provider value={{
      preferences, status, appearanceError, canUndo, update, undo, retry,
    }}>
      {children}
    </PreferencesContext.Provider>
  );
}

export function usePreferences(): PreferencesContextValue {
  const context = useContext(PreferencesContext);
  if (!context) throw new Error("usePreferences requires PreferencesProvider");
  return context;
}
