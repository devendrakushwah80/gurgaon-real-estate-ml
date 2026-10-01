"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { friendlyError, useAuth } from "@/components/auth-provider";
import { Logo } from "@/components/header";

export default function LoginPage() {
  const { user, signIn } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState(""); const [password, setPassword] = useState(""); const [error, setError] = useState(""); const [loading, setLoading] = useState(false);
  useEffect(() => { if (user) router.replace("/dashboard"); }, [router, user]);
  async function submit(event: FormEvent) { event.preventDefault(); setError(""); setLoading(true); try { await signIn(email, password); router.push("/dashboard"); } catch (e) { setError(friendlyError(e)); } finally { setLoading(false); } }
  return <div className="auth-layout"><aside className="auth-aside"><Logo /><div className="auth-quote"><div className="eyebrow">Welcome back</div><h1>Property decisions with more signal.</h1><p>Pick up your Gurgaon search with the valuations, confidence analysis and saved properties that matter to you.</p></div><div className="auth-foot">EstateIQ · Gurgaon property intelligence</div></aside><main className="auth-main"><div className="auth-card"><div className="eyebrow">Sign in</div><h2>Good to see you.</h2><p>Access your recommendations, saved properties and preferences.</p><form className="auth-form" onSubmit={submit}>{error && <div className="form-error" role="alert">{error}</div>}<div className="form-group"><label className="form-label" htmlFor="email">Email</label><input className="form-input" id="email" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} required /></div><div className="form-group"><label className="form-label" htmlFor="password">Password</label><input className="form-input" id="password" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required /></div><button className="button button-dark" disabled={loading}>{loading ? "Signing in…" : "Sign in"}</button></form><div className="auth-switch">Don’t have an account? <Link href="/signup">Create one</Link></div><div className="auth-switch"><Link href="/">Return to home</Link></div></div></main></div>;
}
