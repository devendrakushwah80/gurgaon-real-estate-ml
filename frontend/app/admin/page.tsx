"use client";

import Link from "next/link";
import { BarChart3, Check, ClipboardList, Users, X } from "lucide-react";
import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { AdminOverview, PendingListing } from "@/lib/types";
import { friendlyError, RequireAuth } from "@/components/auth-provider";
import { PageIntro, PublicShell } from "@/components/shell";

function AdminContent() {
  const [overview, setOverview] = useState<AdminOverview | null>(null); const [pending, setPending] = useState<PendingListing[]>([]); const [error, setError] = useState(""); const [busy, setBusy] = useState("");
  async function load() { try { const [summary, queue] = await Promise.all([api.adminOverview(), api.pendingListings()]); setOverview(summary); setPending(queue.properties); } catch (e) { setError(friendlyError(e)); } }
  useEffect(() => { void load(); }, []);
  async function moderate(id: string, action: "approve" | "reject") { setBusy(id); try { await api.moderate(id, action); await load(); } catch (e) { setError(friendlyError(e)); } finally { setBusy(""); } }
  return <PublicShell><div className="container page-wrap"><PageIntro eyebrow="Administration" title="Platform overview." description="Moderation, verification and platform activity for authorized administrators." /><div className="admin-layout"><nav className="side-nav"><Link className="active" href="/admin"><BarChart3 size={14} /> Overview</Link><a href="#queue"><ClipboardList size={14} /> Verification queue</a><a href="#users"><Users size={14} /> Users & agents</a></nav><main className="admin-main">{error && <div className="error-banner">{error}</div>}<div className="stat-grid">{[["Total users", overview?.total_users], ["Active listings", overview?.active_listings], ["Pending reviews", overview?.pending_verifications], ["Low confidence", overview?.low_trust_properties], ["Agent listings", overview?.agent_listings], ["Audit events", overview?.audit_events]].map(([label, value]) => <div className="kpi" key={String(label)}><label>{label}</label><strong>{value ?? "—"}</strong></div>)}</div><section id="queue"><h2>Verification queue</h2>{pending.length ? <div className="data-table-wrap"><table className="data-table"><thead><tr><th>Property</th><th>Agent</th><th>Price</th><th>Status</th><th>Actions</th></tr></thead><tbody>{pending.map((item) => <tr key={item.id}><td><Link className="text-link" href={`/property/${encodeURIComponent(item.id)}`}>{item.title}</Link><br /><span className="table-muted">{item.locality}</span></td><td>{item.owner_id}</td><td>₹{item.listing_price?.toFixed(2)} Cr</td><td><span className="status-badge pending">{item.verification_status}</span></td><td><div className="table-actions"><button className="icon-button table-action approve" aria-label="Approve listing" disabled={busy === item.id} onClick={() => void moderate(item.id, "approve")}><Check size={15} /></button><button className="icon-button table-action reject" aria-label="Reject listing" disabled={busy === item.id} onClick={() => void moderate(item.id, "reject")}><X size={15} /></button></div></td></tr>)}</tbody></table></div> : <div className="empty-state compact-empty"><div className="empty-icon"><ClipboardList size={18} /></div><h3>Queue is clear</h3><p>There are no listings waiting for verification.</p></div>}</section><section className="admin-note" id="users"><h3>Server-side controls remain authoritative</h3><p>Role changes, user management and audit inspection are protected by FastAPI permissions. This frontend never treats hidden navigation as a security boundary.</p></section></main></div></div></PublicShell>;
}

export default function AdminPage() { return <RequireAuth roles={["ADMIN"]}><AdminContent /></RequireAuth>; }
