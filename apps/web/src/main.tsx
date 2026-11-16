import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";
import { TooltipProvider } from "@radix-ui/react-tooltip";

import "./tokens.css";
import "./fonts.css";
import "./styles.css";

import App from "./App";
import { ToastProvider } from "./components/toast";
import { getDesktopBridge } from "./lib/desktop";
import { applyTheme, DEFAULT_PREFERENCES, loadPreferences } from "./lib/preferences";
import { DesignProvider } from "./state/design";
import { JobsProvider } from "./state/jobs";
import { PreferencesProvider } from "./state/preferences";

// The desktop shell declares the title bar height once
// (apps/desktop/main.js → preload bridge). Mirror it into CSS before the
// first paint so the bar, its layout offsets, and the native window-controls
// overlay stay in sync. Browser builds keep the 0px default.
const desktopBridge = getDesktopBridge();
if (desktopBridge) {
  document.documentElement.style.setProperty(
    "--title-bar-height",
    `${desktopBridge.titleBarHeight}px`,
  );
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

async function bootstrap() {
  let initial = { ...DEFAULT_PREFERENCES };
  let loadFailed = false;
  try {
    initial = await loadPreferences();
  } catch {
    loadFailed = true;
  }
  // Apply the saved canvas before mounting; changing themes never remounts
  // the design or job providers, so work in progress remains untouched.
  await applyTheme(initial.theme).catch(() => undefined);
  ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
    <React.StrictMode>
      <PreferencesProvider initial={initial} loadFailed={loadFailed}>
        <QueryClientProvider client={queryClient}>
          <DesignProvider>
            <JobsProvider>
              <TooltipProvider delayDuration={150}>
                <ToastProvider>
                  <BrowserRouter>
                    <App />
                  </BrowserRouter>
                </ToastProvider>
              </TooltipProvider>
            </JobsProvider>
          </DesignProvider>
        </QueryClientProvider>
      </PreferencesProvider>
    </React.StrictMode>,
  );
}

void bootstrap();
