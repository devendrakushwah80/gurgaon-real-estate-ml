"use client";
/* eslint-disable @next/next/no-img-element -- source image hosts are data-driven and not known at build time. */

import Link from "next/link";
import { ExternalLink, Heart, MapPin, Ruler } from "lucide-react";
import { useState } from "react";
import { api, ApiError } from "@/lib/api";
import { formatCrore, formatPercent } from "@/lib/format";
import type { Property } from "@/lib/types";
import { useAuth } from "@/components/auth-provider";
import { PropertyPlaceholder } from "@/components/property-placeholder";
import { ScorePill } from "@/components/score-pill";

export function PropertyCard({ property, compact = false, initialSaved = false }: { property: Property; compact?: boolean; initialSaved?: boolean }) {
  const { user } = useAuth();
  const [saved, setSaved] = useState(initialSaved);
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState("");
  const difference = property.valuation?.difference_percent;

  const toggleSaved = async () => {
    if (!user) { setNotice("Sign in to save properties"); return; }
    setSaving(true); setNotice("");
    try { if (saved) await api.removeFavorite(property.id); else await api.favorite(property.id); setSaved(!saved); }
    catch (error) { setNotice(error instanceof ApiError ? error.message : "Could not update saved properties"); }
    finally { setSaving(false); }
  };

  return <article className={`property-card ${compact ? "compact" : ""}`}>
    <div className="property-image-wrap">
      {property.images?.[0] ? <img src={property.images[0]} alt="Source listing" className="property-image" loading="lazy" /> : <PropertyPlaceholder compact={compact} status={property.listing_status} />}
      <button className={`icon-button favorite-button ${saved ? "saved" : ""}`} aria-label={saved ? "Remove from saved" : "Save property"} onClick={toggleSaved} disabled={saving}><Heart size={17} fill={saved ? "currentColor" : "none"} /></button>
    </div>
    <div className="property-card-content">
      <div className="property-card-heading"><div><span className="source-label">{property.source || "Source data"} · {property.listing_status === "ACTIVE" ? "Verified recently" : property.listing_status === "UNKNOWN" ? "Verification pending" : `Listing status: ${property.listing_status}`}</span><h3>{property.title}</h3></div><span className="property-price">{formatCrore(property.listing_price)}</span></div>
      <div className="property-meta"><span><MapPin size={14} />{property.locality || "Gurgaon"}</span><span>{property.bhk ? `${property.bhk} BHK` : "Configuration unavailable"}</span><span><Ruler size={14} />{property.area_sqft ? `${Math.round(property.area_sqft).toLocaleString()} sqft` : "Area unavailable"}</span></div>
      {!compact && <><div className="card-score-row"><ScorePill type="trust" score={property.trust?.score} /><ScorePill type="investment" score={property.investment?.score} /></div><div className={`valuation-note ${difference !== null && difference < 0 ? "positive" : ""}`}>{formatPercent(difference)} {property.valuation?.classification ? `· ${property.valuation.classification}` : ""}</div>{property.recommendation_reason && <p className="recommendation-reason">{property.recommendation_reason}</p>}</>}
      <div className="property-card-footer"><Link className="text-link" href={`/property/${encodeURIComponent(property.id)}`}>View analysis <span>→</span></Link>{property.source_url && !["REMOVED", "STALE", "UNREACHABLE"].includes(property.listing_status || "") && <a className="source-link" href={property.source_url} target="_blank" rel="noreferrer">Original listing <ExternalLink size={13} /></a>}</div>
      {notice && <div className="inline-note">{notice}</div>}
    </div>
  </article>;
}
