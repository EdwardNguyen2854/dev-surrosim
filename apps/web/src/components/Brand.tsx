/** App identity belongs in content, not in the navigation or desktop title bar. */
export function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <div className="flex items-center gap-2 text-ink">
      <svg viewBox="0 0 32 32" className="h-6 w-6 shrink-0" aria-hidden="true">
        <path
          d="M22 10.2C22 7 19.4 5.2 16.2 5.2 12.4 5.2 9.8 8 9.8 11.4 9.8 14.8 12.4 16 16 16 20 16 22.6 17.4 22.6 20.8 22.6 24.2 20 27 16.2 27 12.8 27 10.4 25.4 10 22"
          fill="none" stroke="currentColor" strokeWidth="4"
          strokeLinecap="round" strokeLinejoin="round"
        />
        <circle cx="10.2" cy="22.2" r="2" className="fill-accent-muted" />
      </svg>
      <span className="font-display text-base font-semibold tracking-tight">SurroSim</span>
      {!compact && (
        <span className="ml-1 hidden border-l border-line pl-3 text-2xs text-ink-muted sm:inline">
          Engineering workbench
        </span>
      )}
    </div>
  );
}
