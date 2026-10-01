"use client";

import Link from "next/link";
import { ArrowRight, Home, Pencil, Plus } from "lucide-react";
import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { Property } from "@/lib/types";
import { RequireAuth } from "@/components/auth-provider";
import { PropertyCard } from "@/components/property-card";
import { PageIntro, PublicShell, SkeletonCards } from "@/components/shell";

function AgentContent() {
  const [properties, setProperties] = useState<Property[]>([]); const [loading, setLoading] = useState(true); const [error, setError] = useState("");
  useEffect(() => { void api.mine().then((response) => setProperties(response.properties)).catch((e) => setError(e instanceof ApiError ? e.message : "Could not load your listings.")).finally(() => setLoading(false)); }, []);
  return <PublicShell><div className="container page-wrap"><PageIntro eyebrow="Agent workspace" title="Your listings, clearly organized." description="Submit source-backed listings, monitor their analysis and request verification when ready." action={<Link className="button button-sage" href="/agent/listings/new"><Plus size={16} /> Add listing</Link>} /><div className="stat-grid"><div className="kpi"><label>Active listings</label><strong>{properties.length}</strong></div><div className="kpi"><label>Pending verification</label><strong>{properties.filter((p) => p.verification_status === "pending").length}</strong></div><div className="kpi"><label>Average Trust Score</label><strong>{properties.length ? Math.round(properties.reduce((sum, item) => sum + (item.trust?.score || 0), 0) / properties.length) : "—"}</strong></div></div>{error && <div className="error-banner">{error}</div>}{loading ? <SkeletonCards count={2} /> : properties.length ? <div className="property-grid">{properties.map((property) => <div key={property.id}><div className="agent-card-actions"><Link className="text-link" href={`/agent/listings/${encodeURIComponent(property.id)}/edit`}><Pencil size={13} /> Edit listing</Link></div><PropertyCard property={property} /></div>)}</div> : <div className="empty-state"><div className="empty-icon"><Home size={18} /></div><h3>No active listings yet</h3><p>Create your first listing with the structured agent form.</p><Link className="button button-sage" href="/agent/listings/new">Add listing <ArrowRight size={15} /></Link></div>}</div></PublicShell>;
}

export default function AgentPage() { return <RequireAuth roles={["AGENT", "ADMIN"]}><AgentContent /></RequireAuth>; }
