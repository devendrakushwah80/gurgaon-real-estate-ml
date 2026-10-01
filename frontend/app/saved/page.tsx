"use client";

import Link from "next/link";
import { ArrowRight, Bookmark, GitCompareArrows } from "lucide-react";
import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { Property } from "@/lib/types";
import { RequireAuth } from "@/components/auth-provider";
import { PropertyCard } from "@/components/property-card";
import { PageIntro, PublicShell, SkeletonCards } from "@/components/shell";

function SavedContent() {
  const [properties, setProperties] = useState<Property[]>([]); const [selected, setSelected] = useState<string[]>([]); const [loading, setLoading] = useState(true); const [error, setError] = useState("");
  useEffect(() => { void load(); }, []);
  async function load() { try { setProperties((await api.favorites()).properties); } catch (e) { setError(e instanceof ApiError ? e.message : "Could not load saved properties."); } finally { setLoading(false); } }
  function toggle(id: string) { setSelected((current) => current.includes(id) ? current.filter((item) => item !== id) : current.length < 4 ? [...current, id] : current); }
  return <PublicShell><div className="container page-wrap"><PageIntro eyebrow="Your shortlist" title="Saved properties." description="Keep the listings worth a closer look together, then compare up to four side by side." action={selected.length >= 2 ? <Link className="button button-sage" href={`/compare?ids=${selected.join(",")}`}><GitCompareArrows size={15} /> Compare {selected.length}</Link> : undefined} />{error && <div className="error-banner">{error}</div>}{loading ? <SkeletonCards count={3} /> : properties.length ? <><div className="selection-note">{selected.length ? `${selected.length} selected for comparison` : "Select 2–4 properties to compare"}</div><div className="property-grid">{properties.map((property) => <div className="selectable-property" key={property.id}><label className="compare-check"><input type="checkbox" checked={selected.includes(property.id)} onChange={() => toggle(property.id)} /><span>Compare</span></label><PropertyCard property={property} initialSaved /></div>)}</div></> : <div className="empty-state"><div className="empty-icon"><Bookmark size={18} /></div><h3>Your shortlist is empty</h3><p>Save properties while exploring Gurgaon to see them here.</p><Link className="button button-sage" href="/properties">Explore properties <ArrowRight size={15} /></Link></div>}</div></PublicShell>;
}

export default function SavedPage() { return <RequireAuth><SavedContent /></RequireAuth>; }
