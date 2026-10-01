import type { Metadata } from "next";
import { AuthProvider } from "@/components/auth-provider";
import "./globals.css";

export const metadata: Metadata = {
  title: "EstateIQ · Gurgaon property intelligence",
  description: "AI-assisted property valuation, trust analysis and investment signals for Gurgaon.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body><AuthProvider>{children}</AuthProvider></body></html>;
}
