import { Link, Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "./components/AppShell";
import { Button, Panel, PanelBody } from "./components/ui";
import { DatasetPage } from "./pages/DatasetPage";
import { ExplorerPage } from "./pages/ExplorerPage";
import { FieldPage } from "./pages/FieldPage";
import { ManualArticlePage } from "./pages/manual/ManualArticlePage";
import { ManualHomePage } from "./pages/manual/ManualHomePage";
import { ModelPage } from "./pages/ModelPage";
import { OptimizePage } from "./pages/OptimizePage";
import { SolverPage } from "./pages/SolverPage";
import { SettingsPage } from "./pages/SettingsPage";
import { VerifyPage } from "./pages/VerifyPage";

function NotFound() {
  return (
    <div className="mx-auto w-full max-w-lg px-7 py-16">
      <Panel>
        <PanelBody className="flex flex-col items-start gap-3">
          <div className="text-2xs font-medium uppercase tracking-wider text-ink-faint">
            404
          </div>
          <h1 className="text-lg font-semibold tracking-tight">Page not found</h1>
          <p className="text-xs text-ink-muted">
            The requested view does not exist in this application.
          </p>
          <Link to="/">
            <Button variant="primary" size="sm">
              Back to Design Explorer
            </Button>
          </Link>
        </PanelBody>
      </Panel>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<ExplorerPage />} />
        <Route path="field" element={<FieldPage />} />
        <Route path="verify" element={<VerifyPage />} />
        <Route path="optimize" element={<OptimizePage />} />
        <Route path="model" element={<ModelPage />} />
        <Route path="dataset" element={<DatasetPage />} />
        <Route path="solver" element={<SolverPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="report" element={<Navigate to="/model" replace />} />
        <Route path="manual" element={<ManualHomePage />} />
        <Route path="manual/:slug" element={<ManualArticlePage />} />
        <Route path="docs" element={<Navigate to="/manual" replace />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}
