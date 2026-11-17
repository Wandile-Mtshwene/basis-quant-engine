"use client";
import type { AssuranceTrace } from "../lib/api";
import { num } from "../lib/api";

// Year-by-year view of exactly how the EPV of benefits is built up.
export function CashflowTable({ trace, issueAge }: { trace: AssuranceTrace; issueAge: number }) {
  const rows = trace.years.map((y, idx) => ({
    year: y,
    age: issueAge + y - 1,
    survival: trace.survival[idx],
    death: trace.death_prob[idx],
    discount: trace.discount[idx],
    contrib: trace.expected_discounted[idx],
  }));

  return (
    <div className="overflow-auto max-h-[420px] rounded-lg border border-border">
      <table className="w-full text-sm">
        <thead className="sticky top-0 bg-surface-2 text-muted">
          <tr className="text-right">
            <th className="px-3 py-2 text-left">Year</th>
            <th className="px-3 py-2">Attained age</th>
            <th className="px-3 py-2">Survival ₜpₓ</th>
            <th className="px-3 py-2">P(death in yr)</th>
            <th className="px-3 py-2">Discount vᵗ</th>
            <th className="px-3 py-2">EPV contribution</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.year} className="text-right border-t border-border/60 hover:bg-surface-2/50">
              <td className="px-3 py-1.5 text-left font-mono">{r.year}</td>
              <td className="px-3 py-1.5 font-mono">{r.age}</td>
              <td className="px-3 py-1.5 font-mono">{num(r.survival, 5)}</td>
              <td className="px-3 py-1.5 font-mono">{num(r.death, 6)}</td>
              <td className="px-3 py-1.5 font-mono">{num(r.discount, 5)}</td>
              <td className="px-3 py-1.5 font-mono text-accent">{num(r.contrib, 7)}</td>
            </tr>
          ))}
        </tbody>
        <tfoot className="sticky bottom-0 bg-surface-2 font-semibold">
          <tr className="text-right">
            <td className="px-3 py-2 text-left" colSpan={5}>
              Sum = EPV of benefits (A)
            </td>
            <td className="px-3 py-2 text-accent font-mono">{num(trace.epv, 7)}</td>
          </tr>
        </tfoot>
      </table>
    </div>
  );
}
