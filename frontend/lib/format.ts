export function formatCrore(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return `₹${value.toFixed(2)} Cr`;
}

export function formatLakhs(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  const lakhs = Math.abs(value * 100);
  return `₹${lakhs >= 100 ? `${(lakhs / 100).toFixed(1)} Cr` : `${lakhs.toFixed(1)} Lakh`}`;
}

export function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "Unavailable";
  return `${Math.abs(value).toFixed(1)}% ${value < 0 ? "below" : value > 0 ? "above" : "near"} estimate`;
}

export function titleCase(value: string): string {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}
