import { useEffect, useRef, useState } from "react";

import { Icon } from "./Icon";

export function CodeBlock({ children, language = "text", label }: {
  children: string;
  language?: string;
  label?: string;
}) {
  const [status, setStatus] = useState<"idle" | "copying" | "copied" | "failed">("idle");
  const codeRef = useRef<HTMLElement>(null);

  useEffect(() => {
    setStatus("idle");
  }, [children]);
  useEffect(() => {
    if (status !== "copied") return;
    const timeout = window.setTimeout(() => setStatus("idle"), 2500);
    return () => window.clearTimeout(timeout);
  }, [status]);

  const copy = async () => {
    setStatus("copying");
    try {
      await navigator.clipboard.writeText(children);
      setStatus("copied");
    } catch {
      setStatus("failed");
    }
  };

  return (
    <div className="overflow-hidden rounded border border-line bg-wash">
      <div className="flex items-center justify-between gap-3 border-b border-line px-3">
        <span className="font-mono text-2xs text-ink-muted">{label ?? language}</span>
        <button type="button" onClick={() => void copy()} disabled={status === "copying"} aria-label={`Copy ${label ?? language} block`} className="inline-flex min-h-11 items-center gap-2 rounded px-2 text-xs font-medium text-ink-muted hover:bg-surface hover:text-ink disabled:opacity-50">
          <Icon name={status === "copied" ? "check" : "copy"} className="h-3.5 w-3.5" />
          {status === "copied" ? "Copied" : status === "copying" ? "Copying…" : status === "failed" ? "Retry copy" : "Copy"}
        </button>
      </div>
      <pre className="thin-scroll m-0 overflow-x-auto px-3 py-3 font-mono text-xs leading-relaxed text-ink"><code ref={codeRef}>{children}</code></pre>
      <div role="status" aria-live="polite" className={status === "failed" ? "border-t border-line p-3 text-xs text-danger" : "sr-only"}>
        {status === "copied" ? "Copied to clipboard." : status === "failed" ? <>
          Clipboard access was denied. <button type="button" className="font-semibold underline" onClick={() => {
            const range = document.createRange();
            if (codeRef.current) range.selectNodeContents(codeRef.current);
            const selection = window.getSelection();
            selection?.removeAllRanges();
            selection?.addRange(range);
          }}>Select the text</button> and copy it with Ctrl+C (Command+C on macOS), or retry.
        </> : ""}
      </div>
    </div>
  );
}
