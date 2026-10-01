import { Suspense } from "react";
import { Header } from "@/components/header";

export function PublicShell({ children }: { children: React.ReactNode }) {
  return <><Suspense><Header /></Suspense><main>{children}</main><footer className="site-footer"><div className="container footer-inner"><div><span className="brand-footer">EstateIQ</span><p>Clearer property decisions for Gurgaon and Indore.</p></div><p className="footer-note">AI-generated estimates and data-driven indicators should be independently verified.</p></div></footer></>;
}

export function PageIntro({ eyebrow, title, description, action }: { eyebrow?: string; title: string; description?: string; action?: React.ReactNode }) {
  return <div className="page-intro"><div><div className="eyebrow">{eyebrow || "EstateIQ · Property intelligence"}</div><h1>{title}</h1>{description && <p>{description}</p>}</div>{action}</div>;
}

export function SkeletonCards({ count = 3 }: { count?: number }) {
  return <div className="property-grid">{Array.from({ length: count }).map((_, index) => <div className="property-skeleton" key={index}><div className="skeleton skeleton-image" /><div className="skeleton skeleton-line wide" /><div className="skeleton skeleton-line" /><div className="skeleton skeleton-line short" /></div>)}</div>;
}
