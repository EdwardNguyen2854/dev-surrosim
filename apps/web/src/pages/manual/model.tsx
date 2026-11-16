import type { ReactNode } from "react";

export type ManualGroupId = "start" | "physics" | "learning" | "app" | "trust";

export type ManualEntry = {
  /** Stable id; also the URL slug for articles. */
  id: string;
  /** Route this entry navigates to. */
  to: string;
  group: ManualGroupId;
  title: string;
  summary: string;
  minutes: number;
  /** True when the page lives outside /manual and renders its own route. */
  standalone?: boolean;
};

export type ManualArticle = ManualEntry & { body: ReactNode };

export const MANUAL_GROUPS: {
  id: ManualGroupId;
  label: string;
  blurb: string;
}[] = [
  {
    id: "start",
    label: "Start here",
    blurb: "The big picture and the vocabulary used everywhere else.",
  },
  {
    id: "physics",
    label: "The physics side",
    blurb: "The real simulation, and the checked answers it produces.",
  },
  {
    id: "learning",
    label: "The learning side",
    blurb: "How the fast models learned from those answers.",
  },
  {
    id: "app",
    label: "Using the workbench",
    blurb: "One guide per page of the app.",
  },
  {
    id: "trust",
    label: "Trust and limits",
    blurb: "Traceability, honest boundaries and common questions.",
  },
];

export function groupLabel(id: ManualGroupId): string {
  return MANUAL_GROUPS.find((group) => group.id === id)?.label ?? id;
}
