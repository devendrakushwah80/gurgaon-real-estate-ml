"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import type { User } from "@/lib/types";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshUser = async () => {
    const token = window.localStorage.getItem("estateiq_token");
    if (!token) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      setUser(await api.me());
    } catch {
      window.localStorage.removeItem("estateiq_token");
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void refreshUser();
  }, []);

  const value = useMemo<AuthContextValue>(() => ({
    user,
    loading,
    signIn: async (email, password) => {
      const response = await api.login(email, password);
      window.localStorage.setItem("estateiq_token", response.access_token);
      setUser(response.user);
    },
    signOut: () => {
      window.localStorage.removeItem("estateiq_token");
      setUser(null);
    },
    refreshUser,
  }), [loading, user]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}

export function RequireAuth({ children, roles }: { children: React.ReactNode; roles?: string[] }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
    if (!loading && user && roles && !roles.some((role) => user.roles.includes(role as never))) router.replace("/dashboard");
  }, [loading, roles, router, user]);

  if (loading || !user || (roles && !roles.some((role) => user.roles.includes(role as never)))) {
    return <div className="page-loading"><div className="spinner" />Checking your session</div>;
  }
  return <>{children}</>;
}

export function friendlyError(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  return "We couldn’t complete that request. Please try again.";
}
