import type {
  AdminOverview,
  LoginResponse,
  MarketInsightsResponse,
  PendingListing,
  Preferences,
  Property,
  PropertyListResponse,
  User,
} from "@/lib/types";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function errorMessage(body: unknown, status: number): string {
  if (typeof body === "object" && body !== null && "detail" in body) {
    const detail = (body as { detail?: unknown }).detail;
    if (typeof detail === "string") return detail;
  }
  if (status === 401) return "Please sign in to continue.";
  if (status === 403) return "You do not have permission to perform this action.";
  if (status === 404) return "The requested resource was not found.";
  return "Something went wrong. Please try again.";
}

export async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = typeof window !== "undefined" ? window.localStorage.getItem("estateiq_token") : null;
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${API_URL}${path}`, { ...options, headers, cache: "no-store" });
  const body = await response.json().catch(() => null);
  if (!response.ok) throw new ApiError(errorMessage(body, response.status), response.status);
  return body as T;
}

export const api = {
  login: (email: string, password: string) => request<LoginResponse>("/api/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  signup: (full_name: string, email: string, password: string) => request<{ id: number; email: string; roles: string[] }>("/api/auth/register", { method: "POST", body: JSON.stringify({ full_name, email, password }) }),
  me: () => request<User>("/api/auth/me"),
  getPreferences: () => request<Preferences>("/api/auth/preferences"),
  updatePreferences: (preferences: Preferences) => request<Preferences>("/api/auth/preferences", { method: "PUT", body: JSON.stringify(preferences) }),
  properties: (params = "") => request<PropertyListResponse>(`/api/properties${params ? `?${params}` : ""}`),
  marketInsights: (city: string) => request<MarketInsightsResponse>(`/api/market/insights?city=${encodeURIComponent(city)}`),
  property: (id: string) => request<Property>(`/api/properties/${encodeURIComponent(id)}`),
  recommendations: (body: Record<string, unknown> = {}) => request<{ recommendations: Property[]; count: number }>("/api/recommendations", { method: "POST", body: JSON.stringify(body) }),
  favorite: (id: string) => request<{ status: string }>(`/api/properties/${encodeURIComponent(id)}/favorite`, { method: "POST", body: "{}" }),
  removeFavorite: (id: string) => request<{ status: string }>(`/api/properties/${encodeURIComponent(id)}/favorite`, { method: "DELETE" }),
  favorites: () => request<{ properties: Property[] }>("/api/properties/user/favorites"),
  compare: (property_ids: string[]) => request<{ properties: Property[]; disclaimer: string }>("/api/properties/compare", { method: "POST", body: JSON.stringify({ property_ids }) }),
  mine: () => request<{ properties: Property[] }>("/api/properties/mine"),
  createListing: (body: Record<string, unknown>) => request<Property>("/api/properties", { method: "POST", body: JSON.stringify(body) }),
  updateListing: (id: string, body: Record<string, unknown>) => request<Property>(`/api/properties/${encodeURIComponent(id)}`, { method: "PUT", body: JSON.stringify(body) }),
  deleteListing: (id: string) => request<{ status: string }>(`/api/properties/${encodeURIComponent(id)}`, { method: "DELETE" }),
  requestVerification: (id: string) => request<{ status: string }>(`/api/properties/${encodeURIComponent(id)}/verification`, { method: "POST", body: "{}" }),
  adminOverview: () => request<AdminOverview>("/api/admin/overview"),
  pendingListings: () => request<{ properties: PendingListing[] }>("/api/admin/properties/pending"),
  moderate: (id: string, action: "approve" | "reject" | "deactivate") => request<{ status: string }>(`/api/admin/properties/${encodeURIComponent(id)}/moderate?action=${action}`, { method: "POST", body: "{}" }),
};
