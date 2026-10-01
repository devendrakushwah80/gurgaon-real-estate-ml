"use client";

import Link from "next/link";
import { SlidersHorizontal, X } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState } from "react";
import { PropertyCard } from "@/components/property-card";
import { PageIntro, PublicShell, SkeletonCards } from "@/components/shell";
import { api, ApiError } from "@/lib/api";
import type { Property } from "@/lib/types";

function PropertiesContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const city = searchParams.get("city")?.toLowerCase() === "indore" ? "indore" : "gurgaon";
  const cityName = city === "indore" ? "Indore" : "Gurgaon";
  const query = searchParams.toString();
  const [properties, setProperties] = useState<Property[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [sort, setSort] = useState("recommended");
  const [locality, setLocality] = useState("");
  const [minBudget, setMinBudget] = useState("");
  const [maxBudget, setMaxBudget] = useState("");
  const [minArea, setMinArea] = useState("");
  const [maxArea, setMaxArea] = useState("");
  const [bhk, setBhk] = useState("");
  const [propertyType, setPropertyType] = useState("");
  const [minTrust, setMinTrust] = useState("");

  useEffect(() => {
    setLocality(searchParams.get("locality") || "");
    setMinBudget(searchParams.get("budget_min") || "");
    setMaxBudget(searchParams.get("budget_max") || "");
    setMinArea(searchParams.get("min_area_sqft") || "");
    setMaxArea(searchParams.get("max_area_sqft") || "");
    setBhk(searchParams.get("bhk") || "");
    setPropertyType(searchParams.get("property_type") || "");
    setMinTrust(searchParams.get("min_trust_score") || "");
  }, [searchParams]);

  useEffect(() => {
    let active = true;
    async function load() {
      setLoading(true);
      try {
        const params = new URLSearchParams(query);
        params.set("city", city);
        params.set("top_n", "50");
        const response = await api.properties(params.toString());
        if (active) {
          setProperties(response.properties);
          setError("");
        }
      } catch (requestError) {
        if (active) setError(requestError instanceof ApiError ? requestError.message : "Could not load properties.");
      } finally {
        if (active) setLoading(false);
      }
    }
    void load();
    return () => { active = false; };
  }, [city, query]);

  function applyFilters() {
    const params = new URLSearchParams({ city });
    if (locality.trim()) params.set("locality", locality.trim());
    if (minBudget) params.set("budget_min", minBudget);
    if (maxBudget) params.set("budget_max", maxBudget);
    if (minArea) params.set("min_area_sqft", minArea);
    if (maxArea) params.set("max_area_sqft", maxArea);
    if (bhk) params.set("bhk", bhk);
    if (propertyType) params.set("property_type", propertyType);
    if (minTrust) params.set("min_trust_score", minTrust);
    router.push(`/properties?${params.toString()}`);
  }

  function clearFilters() {
    setLocality("");
    setMinBudget("");
    setMaxBudget("");
    setMinArea("");
    setMaxArea("");
    setBhk("");
    setPropertyType("");
    setMinTrust("");
    router.push(`/properties?city=${city}`);
  }

  const sorted = useMemo(() => [...properties].sort((a, b) => {
    if (sort === "price-low") return (a.listing_price || 0) - (b.listing_price || 0);
    if (sort === "price-high") return (b.listing_price || 0) - (a.listing_price || 0);
    if (sort === "trust") return (b.trust?.score || 0) - (a.trust?.score || 0);
    if (sort === "investment") return (b.investment?.score || 0) - (a.investment?.score || 0);
    if (sort === "value") return (a.valuation?.difference_percent || 0) - (b.valuation?.difference_percent || 0);
    return (b.recommendation_score || 0) - (a.recommendation_score || 0);
  }), [properties, sort]);

  return (
    <PublicShell>
      <div className="container page-wrap">
        <PageIntro eyebrow={`Explore · ${cityName}`} title={`Properties in ${cityName}, with more context.`} description={`Search ${cityName} by locality, sector, project or area and compare valuation, listing confidence and investment signals.`} />
        <div className="filter-layout">
          <aside className="filter-panel">
            <div className="filter-panel-heading"><h3><SlidersHorizontal size={15} /> Filters</h3><button className="clear-filter" onClick={clearFilters}><X size={12} /> Clear</button></div>
            <div className="filter-field"><label htmlFor="locality">Locality / sector / project</label><input id="locality" value={locality} onChange={(event) => setLocality(event.target.value)} placeholder={city === "indore" ? "Vijay Nagar or Super Corridor" : "Sector 57"} onKeyDown={(event) => { if (event.key === "Enter") applyFilters(); }} /></div>
            <div className="filter-row">
              <div className="filter-field"><label htmlFor="min-budget">Min Cr</label><input id="min-budget" value={minBudget} onChange={(event) => setMinBudget(event.target.value)} inputMode="decimal" /></div>
              <div className="filter-field"><label htmlFor="max-budget">Max Cr</label><input id="max-budget" value={maxBudget} onChange={(event) => setMaxBudget(event.target.value)} inputMode="decimal" /></div>
            </div>
            <div className="filter-row">
              <div className="filter-field"><label htmlFor="min-area">Min area (sqft)</label><input id="min-area" value={minArea} onChange={(event) => setMinArea(event.target.value)} inputMode="numeric" /></div>
              <div className="filter-field"><label htmlFor="max-area">Max area (sqft)</label><input id="max-area" value={maxArea} onChange={(event) => setMaxArea(event.target.value)} inputMode="numeric" /></div>
            </div>
            <div className="filter-field"><label htmlFor="bhk">BHK</label><select id="bhk" value={bhk} onChange={(event) => setBhk(event.target.value)}><option value="">Any</option><option value="1">1</option><option value="2">2</option><option value="3">3</option><option value="4">4</option><option value="5">5</option></select></div>
            <div className="filter-field"><label htmlFor="type">Property type</label><select id="type" value={propertyType} onChange={(event) => setPropertyType(event.target.value)}><option value="">Any type</option><option value="apartment">Apartment</option><option value="house">Independent house / villa</option><option value="plot">Plot / land</option></select></div>
            <div className="filter-field"><label htmlFor="trust">Minimum Trust Score</label><select id="trust" value={minTrust} onChange={(event) => setMinTrust(event.target.value)}><option value="">Any confidence</option><option value="60">60+</option><option value="75">75+</option><option value="90">90+</option></select></div>
            <button className="button button-sage" onClick={applyFilters}>Apply filters</button>
          </aside>
          <section>
            <div className="results-toolbar"><span className="results-count">{loading ? "Finding properties…" : `${sorted.length} properties found in ${cityName}`}</span><select className="sort-select" value={sort} onChange={(event) => setSort(event.target.value)} aria-label="Sort properties"><option value="recommended">Recommended</option><option value="price-low">Price: low to high</option><option value="price-high">Price: high to low</option><option value="trust">Highest Trust Score</option><option value="investment">Highest Investment Score</option><option value="value">Best valuation gap</option></select></div>
            {error ? <div className="error-banner">{error} <button className="text-link" onClick={() => router.refresh()}>Retry</button></div> : loading ? <SkeletonCards count={6} /> : sorted.length ? <div className="property-grid">{sorted.map((property) => <PropertyCard key={property.id} property={property} />)}</div> : <div className="empty-state"><div className="empty-icon"><SlidersHorizontal size={18} /></div><h3>No {cityName} properties matched</h3><p>Try part of a locality or project name, widen your area or budget, or remove a filter.</p><Link className="button button-ghost" href={`/properties?city=${city}`}>Reset search</Link></div>}
          </section>
        </div>
      </div>
    </PublicShell>
  );
}

export default function PropertiesPage() {
  return <Suspense fallback={<PublicShell><div className="page-loading"><div className="spinner" />Loading properties</div></PublicShell>}><PropertiesContent /></Suspense>;
}
