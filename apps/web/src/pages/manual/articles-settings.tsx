import { Link } from "react-router-dom";

import { Steps } from "../../components/content";
import { Callout, Panel, PanelBody, PanelHeader } from "../../components/ui";
import type { ManualArticle } from "./model";

export const appSettings: ManualArticle = {
  id: "app-settings",
  to: "/manual/app-settings",
  group: "app",
  title: "Appearance and navigation",
  summary: "Choose the Light or Black theme, make room with a compact sidebar, and find your way around the manual without changing your engineering work.",
  minutes: 3,
  body: <>
    <Callout title="Your work stays the same" icon="settings">
      Appearance preferences change only how the app looks. Switching themes or
      collapsing navigation does not change a design, stop a job, retrain a
      model, or alter a dataset.
    </Callout>
    <Panel>
      <PanelHeader title="Choose a theme" description="Light is the default; Black is the near-black alternative." />
      <PanelBody>
        <Steps items={[
          { title: "Open Settings", body: <>Use <Link to="/settings" className="text-link underline">Settings</Link> at the bottom of the sidebar. In the desktop app, File → Settings or Ctrl+, (Command+, on macOS) opens the same page.</> },
          { title: "Choose Light or Black", body: "The canvas, text, controls, drawings, and chart labels update immediately. Scientific field colors stay unchanged so their meaning is consistent." },
          { title: "Check the save message", body: "Changes save automatically. If a save fails, the choice stays active for this session and Settings offers Retry save. Undo last change restores the previous appearance choice." },
        ]} />
      </PanelBody>
    </Panel>
    <Panel>
      <PanelHeader title="Make room for your work" />
      <PanelBody className="space-y-3 text-xs text-ink-muted">
        <p>Use the toggle at the top of the sidebar, or turn on “Use a compact sidebar” in Settings. The expanded sidebar keeps its labels; the compact rail keeps the same destinations as icons. Hover over an icon or reach it with the Tab key to see its label.</p>
        <p>In a narrow browser window, use the navigation button beside the SurroSim wordmark. The drawer closes when you choose a page, press Escape, or use its close button. The current page has a highlighted surface and a heavier label, not just a different color.</p>
      </PanelBody>
    </Panel>
    <Panel>
      <PanelHeader title="Read and share the manual" />
      <PanelBody className="space-y-3 text-xs text-ink-muted">
        <p>The documentation home filters topic titles and summaries. It is not a full-text search. Use your browser’s Find command to locate a word inside the article you are reading.</p>
        <p>Browse topics in the left-hand list, or open “Browse manual topics” in a smaller window. Wide windows also show “On this page”. Each section heading has a # link: copy that link address to return to the same passage later. Previous and next links keep the reading order intact.</p>
      </PanelBody>
    </Panel>
    <Panel>
      <PanelHeader title="Where preferences are kept" />
      <PanelBody className="space-y-3 text-xs text-ink-muted">
        <p>In a browser, preferences belong to the current site and browser profile. In the desktop app, they belong to its local user-data folder and survive service port changes. They do not sync between devices or between browser and desktop.</p>
        <p>“Restore defaults” returns to Light with an expanded sidebar. It does not delete engineering data. Reduced motion follows the operating system’s accessibility preference; the theme stays as you chose it rather than following the system automatically.</p>
      </PanelBody>
    </Panel>
  </>,
};
