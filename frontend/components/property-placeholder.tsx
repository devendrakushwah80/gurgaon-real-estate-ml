export function PropertyPlaceholder({ compact = false, status = "UNKNOWN" }: { compact?: boolean; status?: string }) {
  const label = status === "REMOVED" || status === "STALE" || status === "UNREACHABLE" ? "Listing image unavailable" : "Image unavailable in source data";
  return <div className={`property-placeholder ${compact ? "compact" : ""}`} aria-label={label}><div className="placeholder-architecture"><span /><span /><span /><span /></div><small>{label}</small></div>;
}
