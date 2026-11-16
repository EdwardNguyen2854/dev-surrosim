export function formatNumber(
  value: number | null | undefined,
  digits = 4,
): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return "n/a";
  }
  const magnitude = Math.abs(value);
  if (magnitude !== 0 && (magnitude < 1e-3 || magnitude >= 1e5)) {
    return value.toExponential(2);
  }
  return value.toFixed(digits).replace(/\.?0+$/, "");
}

export function formatFixed(
  value: number | null | undefined,
  digits = 2,
): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return "n/a";
  }
  return value.toFixed(digits);
}

export function formatSignedPct(
  value: number | null | undefined,
  digits = 2,
): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return "n/a";
  }
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(digits)}%`;
}

export function formatSeconds(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return "n/a";
  }
  if (value < 1) {
    return `${(value * 1000).toFixed(0)} ms`;
  }
  if (value < 60) {
    return `${value.toFixed(1)} s`;
  }
  const minutes = Math.floor(value / 60);
  const seconds = Math.round(value % 60);
  return `${minutes} min ${seconds} s`;
}

export function shortenHash(value: string | null | undefined, length = 12): string {
  if (!value) {
    return "unknown";
  }
  return value.length > length ? `${value.slice(0, length)}…` : value;
}
