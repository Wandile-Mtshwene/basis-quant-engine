import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Basis — Life & Funeral Pricing Engine",
  description:
    "Transparent actuarial pricing for life and funeral assurance, built on real public mortality tables (2015 VBT, ELT No. 15).",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col">
        <header className="border-b border-border bg-surface/60 backdrop-blur sticky top-0 z-10">
          <div className="mx-auto max-w-6xl px-5 h-14 flex items-center justify-between">
            <Link href="/" className="flex items-center gap-2 font-semibold">
              <span className="inline-block h-5 w-5 rounded bg-accent" />
              Basis<span className="text-muted font-normal">Pricing Engine</span>
            </Link>
            <nav className="flex items-center gap-5 text-sm text-muted">
              <Link href="/" className="hover:text-foreground">Quote</Link>
              <Link href="/retirement" className="hover:text-foreground">Retirement</Link>
              <Link href="/admin" className="hover:text-foreground">Admin basis</Link>
              <a href="/api/docs" target="_blank" rel="noreferrer" className="hover:text-foreground">
                API docs ↗
              </a>
            </nav>
          </div>
        </header>
        <main className="flex-1">{children}</main>
        <footer className="border-t border-border text-muted text-xs">
          <div className="mx-auto max-w-6xl px-5 py-4 flex flex-wrap gap-x-6 gap-y-1 justify-between">
            <span>Open-core actuarial engine · Python · FastAPI · Next.js</span>
            <span>Tables: 2015 VBT (life) · ELT No. 15 1990-92 (funeral). Illustrative demo basis.</span>
          </div>
        </footer>
      </body>
    </html>
  );
}
