export type Role = "USER" | "AGENT" | "ADMIN";

export interface User {
  id: number;
  email: string;
  full_name: string;
  is_active?: boolean;
  roles: Role[];
}

export interface FairValue {
  listing_price: number | null;
  fair_value: number;
  difference_value: number | null;
  difference_percent: number | null;
  classification: string;
  estimate_source?: string;
  disclaimer: string;
}

export interface TrustScore {
  score: number;
  label: string;
  breakdown: Record<string, number>;
  positive_signals: string[];
  warnings: string[];
  method?: string;
}

export interface InvestmentScore {
  score: number;
  label: string;
  breakdown: Record<string, number>;
  positive_signals: string[];
  warnings: string[];
}

export interface Property {
  id: string;
  owner_id?: number | null;
  source: string;
  source_listing_id?: string | null;
  source_url?: string | null;
  title: string;
  description?: string | null;
  property_type?: string | null;
  bhk?: number | null;
  locality?: string | null;
  sector?: string | null;
  city?: string | null;
  area_sqft?: number | null;
  listing_price?: number | null;
  price_per_sqft?: number | null;
  furnishing?: string | null;
  floor?: string | null;
  total_floors?: number | null;
  property_age?: string | null;
  amenities: string[];
  images: string[];
  seller_type?: string | null;
  rera_id?: string | null;
  status?: string;
  verification_status?: string;
  listing_status?: "ACTIVE" | "STALE" | "REMOVED" | "UNREACHABLE" | "UNKNOWN" | string;
  status_reason?: string | null;
  last_verified_at?: string | null;
  project_name?: string | null;
  image_source?: string | null;
  image_verified_at?: string | null;
  image_match_confidence?: number | null;
  valuation: FairValue;
  trust: TrustScore;
  investment: InvestmentScore;
  recommendation_score?: number;
  recommendation_reason?: string;
}

export interface Preferences {
  budget_min?: number | null;
  budget_max?: number | null;
  preferred_bhk: number[];
  preferred_localities: string[];
  property_type?: string | null;
  min_area_sqft?: number | null;
  furnishing?: string | null;
  usage?: string | null;
  min_trust_score: number;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in_minutes: number;
  user: User;
}

export interface PropertyListResponse {
  properties: Property[];
  count: number;
  image_data_note?: string;
}

export interface MarketLocalityInsight {
  locality: string;
  median_price_per_sqft: number;
  median_listing_price: number | null;
  median_area_sqft: number | null;
  listing_count: number;
}

export interface MarketInsightsResponse {
  city: string;
  summary: {
    city_median_price_per_sqft: number | null;
    listing_count: number;
    locality_count: number;
    highest_locality: string | null;
    lowest_locality: string | null;
  };
  localities: MarketLocalityInsight[];
}

export interface AdminOverview {
  total_users: number;
  agent_listings: number;
  active_listings: number;
  pending_verifications: number;
  audit_events: number;
  low_trust_properties: number;
}

export interface PendingListing {
  id: string;
  owner_id: number;
  title: string;
  locality: string;
  listing_price: number;
  verification_status: string;
  updated_at: string;
}
