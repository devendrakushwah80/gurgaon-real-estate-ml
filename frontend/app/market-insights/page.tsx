"use client";

import Link from "next/link";
import { ArrowUpRight, BarChart3, MapPin, TrendingUp } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { CSSProperties, Suspense, useEffect, useMemo, useState } from "react";
import { PageIntro, PublicShell } from "@/components/shell";
import { api, ApiError } from "@/lib/api";
import type { MarketInsightsResponse, MarketLocalityInsight } from "@/lib/types";

const bubbleColors = ["#3f7258", "#d4815c", "#5d79a6", "#b49345", "#7c6598", "#368d91", "#b65f6a", "#728f4d"];

function moneyPerSqft(value: number | null) {
  return value ? `₹${Math.round(value).toLocaleString("en-IN")}/sqft` : "Not available";
}

function bubbleSize(item: MarketLocalityInsight, maxCount: number) {
  const weight = maxCount > 1 ? Math.sqrt(item.listing_count / maxCount) : 1;
  return Math.round(118 + weight * 92);
}

function MarketInsightsContent() {
  const searchParams = useSearchParams();
  const city = searchParams.get("city")?.toLowerCase() === "indore" ? "indore" : "gurgaon";
  const cityName = city === "indore" ? "Indore" : "Gurgaon";
  const [data, setData] = useState<MarketInsightsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    async function load() {
      setLoading(true);
      try {
        const response = await api.marketInsights(city);
        if (active) { setData(response); setError(""); }
      } catch (requestError) {
        if (active) setError(requestError instanceof ApiError ? requestError.message : "Could not load market insights.");
      } finally {
        if (active) setLoading(false);
      }
    }
    void load();
    return () => { active = false; };
  }, [city]);

  const bubbles = useMemo(() => data?.localities.slice(0, 24) || [], [data]);
  const maxCount = Math.max(1, ...bubbles.map((item) => item.listing_count));
  const medianRate = data?.summary.city_median_price_per_sqft || 0;

  return (
    <PublicShell>
      <div className="container page-wrap market-page">
        <PageIntro eyebrow={`Market insights · ${cityName}`} title={`${cityName} price-per-sqft map.`} description={`Compare locality-level median asking rates from EstateIQ's current ${cityName} listings. Circle size represents listing coverage; colour separates localities for quick comparison.`} action={<Link className="button button-sage" href={`/properties?city=${city}`}>Explore {cityName} listings <ArrowUpRight size={15} /></Link>} />

        {error ? <div className="error-banner">{error}</div> : loading ? <div className="market-loading"><div className="spinner" />Calculating {cityName} locality insights…</div> : !data || !data.localities.length ? <div className="empty-state"><div className="empty-icon"><BarChart3 size={18} /></div><h3>No market data for {cityName} yet</h3><p>Price-per-sqft insights appear after listings with locality, area and price data are ingested.</p></div> : <>
          <section className="insight-summary" aria-label={`${cityName} market summary`}>
            <article className="insight-stat"><span><TrendingUp size={15} /> City median</span><strong>{moneyPerSqft(data.summary.city_median_price_per_sqft)}</strong><small>Across {data.summary.listing_count} usable listings</small></article>
            <article className="insight-stat"><span><MapPin size={15} /> Localities compared</span><strong>{data.summary.locality_count}</strong><small>Highest: {data.summary.highest_locality || "—"}</small></article>
            <article className="insight-stat"><span><BarChart3 size={15} /> Price range</span><strong>{data.summary.highest_locality || "—"}</strong><small>Lowest: {data.summary.lowest_locality || "—"}</small></article>
          </section>

          <section className="market-panel">
            <div className="section-heading"><div><div className="eyebrow">Locality bubble view</div><h2>What one square foot costs</h2><p>Select any circle to open matching {cityName} listings.</p></div><div className="bubble-legend"><span className="legend-dot" /> Larger circle = more listings</div></div>
            <div className="bubble-field">
              {bubbles.map((item, index) => {
                const size = bubbleSize(item, maxCount);
                const style: CSSProperties = { width: size, height: size, backgroundColor: bubbleColors[index % bubbleColors.length] };
                return <Link className="market-bubble" style={style} href={`/properties?city=${city}&locality=${encodeURIComponent(item.locality)}`} key={item.locality} title={`${item.locality}: ${moneyPerSqft(item.median_price_per_sqft)} from ${item.listing_count} listings`}><strong>{item.locality}</strong><span>{moneyPerSqft(item.median_price_per_sqft)}</span><small>{item.listing_count} listing{item.listing_count === 1 ? "" : "s"}</small></Link>;
              })}
            </div>
          </section>

          <section className="market-panel comparison-panel">
            <div className="section-heading"><div><div className="eyebrow">Side-by-side comparison</div><h2>{cityName} locality rates</h2><p>Median asking price per square foot, ordered from highest to lowest.</p></div></div>
            <div className="market-comparison" role="table" aria-label={`${cityName} locality price comparison`}>
              <div className="market-row market-row-head" role="row"><span>Locality</span><span>Price / sqft</span><span>Vs city median</span><span>Coverage</span><span /></div>
              {data.localities.map((item) => {
                const difference = medianRate ? ((item.median_price_per_sqft - medianRate) / medianRate) * 100 : 0;
                return <div className="market-row" role="row" key={item.locality}><strong>{item.locality}</strong><span>{moneyPerSqft(item.median_price_per_sqft)}</span><span className={difference >= 0 ? "rate-above" : "rate-below"}>{difference >= 0 ? "+" : ""}{difference.toFixed(1)}%</span><span>{item.listing_count} listing{item.listing_count === 1 ? "" : "s"}</span><Link href={`/properties?city=${city}&locality=${encodeURIComponent(item.locality)}`} aria-label={`View ${item.locality} listings`}>View <ArrowUpRight size={13} /></Link></div>;
              })}
            </div>
          </section>
          <p className="market-disclaimer">Figures are medians from available source listings, not registered transaction prices. Low listing counts can make a locality estimate less stable.</p>
        </>}
      </div>
    </PublicShell>
  );
}

export default function MarketInsightsPage() {
  return <Suspense fallback={<PublicShell><div className="page-loading"><div className="spinner" />Loading market insights</div></PublicShell>}><MarketInsightsContent /></Suspense>;
}
