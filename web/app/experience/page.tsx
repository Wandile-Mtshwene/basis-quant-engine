"use client";

import { useEffect, useState } from "react";
import { analyseExperience, type ExperienceResult, type ExperienceSegment } from "../lib/api";

const DIMS = [
  { key: "age_band", label: "Age band" },
  { key: "sex", label: "Sex" },
  { key: "smoker_status", label: "Smoker status" },
];

export default function Experience() {
  const [by, setBy] = useState<string[]>(["age_band", "smoker_status"]);
  const [res, setRes] = useState<ExperienceResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(dims: string[]) {
    setLoading(true); setError(null);
    try { setRes(await analyseExperience(dims.length ? dims : ["smoker_status"])); }
    catch (e) { setError(e instanceof Error ? e.message : "failed"); setRes(null); }
    finally { setLoading(false); }
  }
  useEffect(() => { run(by); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, []);

  const toggle = (k: string) => {
    const next = by.includes(k) ? by.filter((d) => d !== k) : [...by, k];
    setBy(next); run(next);
  };

  // scale A/E bars around a 100% reference
  const maxAE = res ? Math.max(120, ...res.segments.map((s) => s.ae_pct), res.overall.ae_pct) : 120;

  return (
    <div className="mx-auto max-w-6xl px-5 py-8">
      <h1 className="text-2xl font-semibold">Experience analysis studio</h1>
      <p className="text-muted mt-1 max-w-3xl text-sm">
        Actual-versus-expected mortality on a synthetic book of {res ? Number(res.overall.exposure).toLocaleString() : "—"} life-years,
        measured against the 2015 VBT ultimate basis. Small, noisy cells are tempered by limited-fluctuation
        credibility, so the credible A/E is what you would actually set assumptions from.
      </p>

      <div className="flex flex-wrap items-center gap-2 mt-5">
        <span className="field-label mr-1">Group by</span>
        {DIMS.map((d) => (
          <button key={d.key} onClick={() => toggle(d.key)}
            className={`px-3 py-1.5 rounded-lg text-sm border transition ${
              by.includes(d.key)
                ? "bg-accent text-[var(--accent-ink)] border-transparent font-semibold"
                : "border-border text-muted hover:text-foreground"}`}>
            {d.label}
          </button>
        ))}
        {loading && <span className="text-muted text-sm ml-2">analysing…</span>}
        {error && <span className="text-warn text-sm ml-2">{error}</span>}
      </div>

      {res && (
        <div className="card mt-5 overflow-hidden">
          <div className="overflow-auto">
            <table className="w-full text-sm">
              <thead className="bg-surface-2 text-muted">
                <tr className="text-right">
                  {res.by.map((b) => <th key={b} className="px-3 py-2 text-left capitalize">{b.replace("_", " ")}</th>)}
                  <th className="px-3 py-2">Exposure</th>
                  <th className="px-3 py-2">Actual</th>
                  <th className="px-3 py-2">Expected</th>
                  <th className="px-3 py-2 text-left w-[32%]">A/E (raw vs credible)</th>
                  <th className="px-3 py-2">Credibility</th>
                </tr>
              </thead>
              <tbody>
                {res.segments.map((s, i) => <SegmentRow key={i} s={s} dims={res.by} maxAE={maxAE} />)}
              </tbody>
              <tfoot className="bg-surface-2 font-semibold">
                <SegmentRow s={res.overall} dims={res.by} maxAE={maxAE} label="Overall" />
              </tfoot>
            </table>
          </div>
        </div>
      )}

      <p className="text-muted text-xs mt-3">
        Bars are centred on the 100% expected line. Full credibility is reached at {res?.full_credibility_claims ?? 1082} expected
        claims (90% confidence within 5%). Credible A/E = Z × raw A/E + (1 − Z) × 100%.
      </p>
    </div>
  );
}

function SegmentRow({ s, dims, maxAE, label }: { s: ExperienceSegment; dims: string[]; maxAE: number; label?: string }) {
  const ref = (100 / maxAE) * 100;      // position of the 100% reference line, %
  const raw = (s.ae_pct / maxAE) * 100;
  const cred = (s.credible_ae_pct / maxAE) * 100;
  const worse = s.credible_ae_pct > 100;
  return (
    <tr className="text-right border-t border-border/60">
      {label
        ? <td className="px-3 py-2 text-left" colSpan={dims.length || 1}>{label}</td>
        : dims.map((d) => <td key={d} className="px-3 py-2 text-left">{String(s[d])}</td>)}
      <td className="px-3 py-2 font-mono">{Number(s.exposure).toLocaleString()}</td>
      <td className="px-3 py-2 font-mono">{s.actual}</td>
      <td className="px-3 py-2 font-mono">{Number(s.expected).toFixed(0)}</td>
      <td className="px-3 py-2">
        <div className="relative h-5 rounded bg-surface-2">
          <div className="absolute inset-y-0 border-l border-muted/60" style={{ left: `${ref}%` }} />
          <div className="absolute inset-y-0 rounded opacity-30"
            style={{ left: `${Math.min(raw, ref)}%`, width: `${Math.abs(raw - ref)}%`, background: worse ? "#f87171" : "var(--positive)" }} />
          <div className="absolute inset-y-1 rounded"
            style={{ left: `${Math.min(cred, ref)}%`, width: `${Math.abs(cred - ref)}%`, background: worse ? "#f87171" : "var(--positive)" }} />
        </div>
        <div className="flex justify-between text-xs mt-0.5 font-mono text-muted">
          <span>raw {s.ae_pct}%</span>
          <span className="text-foreground">credible {s.credible_ae_pct}%</span>
        </div>
      </td>
      <td className="px-3 py-2 font-mono">{(s.credibility * 100).toFixed(0)}%</td>
    </tr>
  );
}
