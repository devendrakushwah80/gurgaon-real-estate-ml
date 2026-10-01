"use client";
/* eslint-disable @next/next/no-img-element -- source image hosts are data-driven and not known at build time. */

import Link from "next/link";
import { ArrowLeft, CheckCircle2, X } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { formatCrore, formatPercent, titleCase } from "@/lib/format";
import type { Property } from "@/lib/types";
import { RequireAuth } from "@/components/auth-provider";
import { PageIntro, PublicShell } from "@/components/shell";
import { PropertyPlaceholder } from "@/components/property-placeholder";
import { ScorePill } from "@/components/score-pill";

function CompareContent() {
  const searchParams = useSearchParams(); const idsKey = searchParams.get("ids") || ""; const ids = idsKey.split(",").filter(Boolean); const [properties, setProperties] = useState<Property[]>([]); const [error, setError] = useState("");
  useEffect(() => { const requestedIds = idsKey.split(",").filter(Boolean); if (requestedIds.length >= 2) { void api.compare(requestedIds).then((response) => setProperties(response.properties)).catch((e) => setError(e instanceof ApiError ? e.message : "Could not compare these properties.")); } }, [idsKey]);
  if (ids.length < 2) return <PublicShell><div className="container page-wrap"><div className="empty-state"><h3>Select at least two properties</h3><p>Choose properties from your saved shortlist to compare them here.</p><Link className="button button-sage" href="/saved">Go to saved properties</Link></div></div></PublicShell>;
  const rows: [string, (property: Property) => React.ReactNode][] = [["Listed price", (p) => formatCrore(p.listing_price)], ["Estimated fair value", (p) => formatCrore(p.valuation?.fair_value)], ["Valuation gap", (p) => formatPercent(p.valuation?.difference_percent)], ["Trust Score", (p) => <ScorePill type="trust" score={p.trust?.score} />], ["Investment Score", (p) => <ScorePill type="investment" score={p.investment?.score} />], ["Configuration", (p) => p.bhk ? `${p.bhk} BHK` : "Unavailable"], ["Area", (p) => p.area_sqft ? `${Math.round(p.area_sqft).toLocaleString()} sqft` : "Unavailable"], ["Locality", (p) => p.locality || "Unavailable"], ["Property type", (p) => p.property_type || "Unavailable"], ["Furnishing", (p) => p.furnishing || "Unavailable"], ["Amenities", (p) => p.amenities?.length ? p.amenities.slice(0, 5).join(", ") : "Unavailable"], ["Source", (p) => p.source || "Unavailable"]];
  return <PublicShell><div className="container page-wrap"><Link className="back-link" href="/saved"><ArrowLeft size={14} /> Back to saved</Link><PageIntro eyebrow="Side by side" title="Compare with context." description="A structured comparison of the data EstateIQ has available. It is not a purchase recommendation." />{error ? <div className="error-banner">{error}</div> : <div className="compare-table"><div className="compare-label-column"><div className="compare-label-spacer" />{rows.map(([label]) => <div className="compare-label" key={label}>{label}</div>)}</div>{properties.map((property) => <div className="compare-column" key={property.id}><div className="compare-property-head">{property.images?.[0] ? <img src={property.images[0]} alt="Source listing" /> : <PropertyPlaceholder compact />}<Link href={`/property/${encodeURIComponent(property.id)}`}><strong>{property.title}</strong></Link><span>{property.locality}</span></div>{rows.map(([label, render]) => <div className="compare-value" key={label}>{render(property)}</div>)}</div>)}</div>}</div></PublicShell>;
}

export default function ComparePage() { return <Suspense fallback={<PublicShell><div className="page-loading"><div className="spinner" />Loading comparison</div></PublicShell>}><RequireAuth><CompareContent /></RequireAuth></Suspense>; }
