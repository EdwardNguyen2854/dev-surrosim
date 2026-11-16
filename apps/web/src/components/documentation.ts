import { createContext } from "react";

/** Opt reading surfaces into stable section anchors without changing workbench panels. */
export const DocumentationContext = createContext(false);

export function sectionId(title: string): string {
  return `section-${title.toLowerCase().normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "").replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "")}`;
}
