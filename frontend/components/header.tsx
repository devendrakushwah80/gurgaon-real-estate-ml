"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { ArrowRight, Menu, X } from "lucide-react";
import { useState } from "react";
import { useAuth } from "@/components/auth-provider";

export function Logo() {
  return <Link className="brand" href="/"><span className="brand-mark">E</span><span>Estate<span className="brand-accent">IQ</span></span></Link>;
}

export function Header() {
  const { user, signOut } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [open, setOpen] = useState(false);
  const city = searchParams.get("city")?.toLowerCase() === "indore" ? "indore" : "gurgaon";
  function changeCity(value: string) {
    const params = new URLSearchParams(searchParams.toString());
    params.set("city", value);
    router.push(`${pathname === "/market-insights" ? "/market-insights" : "/properties"}?${params.toString()}`);
    setOpen(false);
  }
  const links = [["Explore", `/properties?city=${city}`], ["Market insights", `/market-insights?city=${city}`], ["How it works", `/?city=${city}#how-it-works`]];
  return (
    <header className="site-header">
      <div className="container header-inner">
        <Logo />
        <nav className={`main-nav ${open ? "mobile-open" : ""}`}>
          {links.map(([label, href]) => <Link className={pathname === href.split("?")[0] ? "active" : ""} href={href} key={label} onClick={() => setOpen(false)}>{label}</Link>)}
          {user && <Link className={pathname.startsWith("/dashboard") ? "active" : ""} href="/dashboard" onClick={() => setOpen(false)}>Dashboard</Link>}
          {user?.roles.includes("AGENT") && <Link href="/agent" onClick={() => setOpen(false)}>Agent</Link>}
          {user?.roles.includes("ADMIN") && <Link href="/admin" onClick={() => setOpen(false)}>Admin</Link>}
        </nav>
        <div className="header-actions">
          <label className="city-switcher"><span className="sr-only">City</span><select value={city} onChange={(event) => changeCity(event.target.value)} aria-label="Choose city"><option value="gurgaon">Gurgaon</option><option value="indore">Indore</option></select></label>
          {user ? <>
            <Link className="avatar-link" href="/profile">{(user.full_name || user.email).slice(0, 1).toUpperCase()}</Link>
            <button className="button button-ghost desktop-only" onClick={() => { signOut(); router.push("/"); }}>Log out</button>
          </> : <>
            <Link className="button button-ghost desktop-only" href="/login">Sign in</Link>
            <Link className="button button-dark" href="/signup">Get started <ArrowRight size={15} /></Link>
          </>}
          <button className="menu-button" aria-label="Toggle navigation" onClick={() => setOpen(!open)}>{open ? <X size={21} /> : <Menu size={21} />}</button>
        </div>
      </div>
    </header>
  );
}
