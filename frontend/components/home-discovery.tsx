"use client";

import Link from "next/link";
import { ArrowRight, CheckCircle2, Search } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { Property } from "@/lib/types";
import { PropertyCard } from "@/components/property-card";
import { SkeletonCards } from "@/components/shell";

export function HomeDiscovery() {
  const [properties, setProperties] = useState<Property[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [locality, setLocality] = useState("");
  const [budget, setBudget] = useState("");
  const [bhk, setBhk] = useState("");

  useEffect(() => { void load(); }, []);
  async function load(query = "") { setLoading(true); try { const response = await api.properties(`top_n=6${query}`); setProperties(response.properties); setError(""); } catch (e) { setError(e instanceof ApiError ? "The discovery service is unavailable right now." : "Could not load properties."); } finally { setLoading(false); } }
  function search(event: FormEvent) { event.preventDefault(); const params = new URLSearchParams(); if (locality) params.set("locality", locality); if (budget) params.set("budget_max", budget); if (bhk) params.set("bhk", bhk); window.location.href = `/properties?${params.toString()}`; }

  return <>
    <section className="hero"><div className="container hero-grid"><div><div className="eyebrow">Property intelligence for Gurgaon</div><h1>Make a clearer <em>property</em> decision.</h1><p className="hero-copy">EstateIQ brings valuation, listing confidence and investment signals together so you can explore Gurgaon with better context.</p><div className="hero-actions"><Link className="button button-dark button-large" href="/properties">Explore properties <ArrowRight size={16} /></Link><a className="button button-ghost button-large" href="#how-it-works">How it works</a></div><div className="hero-note"><CheckCircle2 size={14} /> AI-generated estimates. Independent due diligence still matters.</div></div><div className="hero-visual" aria-label="Illustrated Gurgaon property landscape"><div className="building" /><div className="hero-visual-card"><p>EstateIQ estimate</p><strong>₹1.90 Cr</strong><small>4.2% below listing estimate</small></div></div></div></section>
    <div className="container"><form className="search-panel" onSubmit={search}><div className="search-field"><label htmlFor="home-locality">Where</label><input id="home-locality" value={locality} onChange={(e) => setLocality(e.target.value)} placeholder="Sector or locality" /></div><div className="search-field"><label htmlFor="home-budget">Budget up to</label><input id="home-budget" value={budget} onChange={(e) => setBudget(e.target.value)} inputMode="decimal" placeholder="₹ Crore" /></div><div className="search-field"><label htmlFor="home-bhk">Configuration</label><select id="home-bhk" value={bhk} onChange={(e) => setBhk(e.target.value)}><option value="">Any BHK</option><option value="2">2 BHK</option><option value="3">3 BHK</option><option value="4">4 BHK</option><option value="5">5 BHK</option></select></div><button className="button button-sage" type="submit"><Search size={16} /> Search</button></form></div>
    <section className="section"><div className="container"><div className="section-heading"><div><div className="eyebrow">Curated from available source data</div><h2>Start with the right context</h2><p>Explore properties with fair-value, confidence and investment signals in one view.</p></div><Link className="text-link" href="/properties">View all properties →</Link></div>{loading ? <SkeletonCards count={3} /> : error ? <div className="empty-state"><div className="empty-icon"><Search size={18} /></div><h3>Discovery is taking a moment</h3><p>{error}</p><button className="button button-ghost" onClick={() => void load()}>Try again</button></div> : <div className="property-grid">{properties.slice(0, 3).map((property) => <PropertyCard key={property.id} property={property} />)}</div>}</div></section>
    <section className="section section-soft"><div className="container"><div className="section-heading"><div><div className="eyebrow">What EstateIQ looks at</div><h2>Signals, not promises</h2></div></div><div className="trust-strip"><div className="trust-strip-card"><div className="eyebrow">01 · Valuation</div><strong>Fair-value context</strong><p>Compare a listing with an AI-generated estimate based on available property data.</p></div><div className="trust-strip-card"><div className="eyebrow">02 · Confidence</div><strong>Listing trust</strong><p>See completeness, source, consistency and freshness signals without absolute claims.</p></div><div className="trust-strip-card"><div className="eyebrow">03 · Investment</div><strong>Market perspective</strong><p>Understand valuation advantage, demand proxies and data limitations separately.</p></div></div></div></section>
    <section className="section" id="how-it-works"><div className="container"><div className="section-heading"><div><div className="eyebrow">A calmer way to explore</div><h2>How EstateIQ works</h2></div></div><div className="how-grid"><div className="how-card"><span>01</span><h3>Find a fit</h3><p>Search by locality, configuration, budget and property type across the source-backed catalog.</p></div><div className="how-card"><span>02</span><h3>Read the analysis</h3><p>Review fair value, Trust Score and Investment Score with their underlying breakdowns.</p></div><div className="how-card"><span>03</span><h3>Do your diligence</h3><p>Use EstateIQ as decision support, then verify documents, authenticity and financial assumptions independently.</p></div></div></div></section>
  </>;
}
