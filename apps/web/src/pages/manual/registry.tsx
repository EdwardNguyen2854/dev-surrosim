import { appExplorer, appField, appOptimize, appVerify } from "./articles-app";
import { surrogates, trust } from "./articles-learning";
import { designSpace, groundTruth } from "./articles-physics";
import { glossary, overview } from "./articles-start";
import { faq, limitations, provenance } from "./articles-trust";
import { appSettings } from "./articles-settings";
import type { ManualArticle, ManualEntry } from "./model";

/*
 * The manual is one ordered set of entries. Articles live under /manual/<id>;
 * the solver entry is a standalone page (/solver) that shares the manual
 * chrome, so the reading order stays continuous even though the route changes.
 */
export const SOLVER_ENTRY: ManualEntry = {
  id: "solver",
  to: "/solver",
  group: "physics",
  title: "The solver",
  summary:
    "What happens inside a real finite-element solve, step by step — and the evidence that its answers are right.",
  minutes: 7,
  standalone: true,
};

export const MANUAL_ARTICLES: ManualArticle[] = [
  overview,
  glossary,
  designSpace,
  groundTruth,
  surrogates,
  trust,
  appExplorer,
  appField,
  appVerify,
  appOptimize,
  appSettings,
  provenance,
  limitations,
  faq,
];

export const MANUAL_ENTRIES: ManualEntry[] = [
  overview,
  glossary,
  designSpace,
  SOLVER_ENTRY,
  groundTruth,
  surrogates,
  trust,
  appExplorer,
  appField,
  appVerify,
  appOptimize,
  appSettings,
  provenance,
  limitations,
  faq,
];

export function articleById(id: string): ManualArticle | undefined {
  return MANUAL_ARTICLES.find((article) => article.id === id);
}

export function entryById(id: string): ManualEntry | undefined {
  return MANUAL_ENTRIES.find((entry) => entry.id === id);
}

export function manualNeighbours(id: string): {
  previous: ManualEntry | null;
  next: ManualEntry | null;
} {
  const index = MANUAL_ENTRIES.findIndex((entry) => entry.id === id);
  if (index === -1) {
    return { previous: null, next: null };
  }
  return {
    previous: index > 0 ? MANUAL_ENTRIES[index - 1] : null,
    next: index < MANUAL_ENTRIES.length - 1 ? MANUAL_ENTRIES[index + 1] : null,
  };
}
