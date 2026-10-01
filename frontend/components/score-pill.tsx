import { ShieldCheck, TrendingUp } from "lucide-react";

export function ScorePill({ type, score }: { type: "trust" | "investment"; score: number | undefined }) {
  const trust = type === "trust";
  return <span className={`score-pill ${trust ? "score-trust" : "score-investment"}`}><span>{trust ? <ShieldCheck size={14} /> : <TrendingUp size={14} />}{trust ? "Trust" : "Investment"}</span><strong>{score ?? "—"}</strong></span>;
}

export function ScoreBar({ label, value, max = 100 }: { label: string; value: number; max?: number }) {
  return <div className="score-bar-row"><div><span>{label}</span><strong>{value}/{max}</strong></div><div className="score-track"><span style={{ width: `${Math.max(0, Math.min(100, value / max * 100))}%` }} /></div></div>;
}
