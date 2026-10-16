/** Class name merge helper (clsx + tailwind-merge compatible). */
export function cn(...classes: Array<string | false | null | undefined>): string {
  return classes.filter(Boolean).join(" ");
}

/** Format a delta value with a sign and percent suffix for MetricCard trends. */
export function formatTrend(value: number, percent: number): string {
  const arrow = value >= 0 ? "\u2191" : "\u2193";
  const sign = percent >= 0 ? "+" : "";
  return `${arrow} ${value} ${sign}${percent}%`;
}
