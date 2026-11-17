"use client";

import { useState } from "react";
import { assessCredit, zar, type CreditRequest, type CreditDecision } from "../lib/api";

const DEFAULTS: CreditRequest = {
  age: 35, employment_type: "permanent", employment_months: 36, existing_accounts: 2,
  adverse_history: false, gross_monthly_income: 45_000, net_monthly_income: 33_000,
  monthly_living_expenses: 12_000, existing_monthly_debt: 4_000,
  loan_amount: 150_000, annual_rate: 0.18, term_months: 48,
};

const DECISION_STYLE: Record<string, { bg: string; label: string }> = {
  approve: { bg: "var(--positive)", label: "Approved" },
  refer: { bg: "var(--warn)", label: "Refer — manual review" },
  decline: { bg: "#f87171", label: "Declined" },
};

export default function Credit() {
  const [req, setReq] = useState<CreditRequest>(DEFAULTS);
  const [res, setRes] = useState<CreditDecision | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const setN = (k: keyof CreditRequest) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setReq({ ...req, [k]: +e.target.value });
  const setV = (k: keyof CreditRequest, v: string | boolean) => setReq({ ...req, [k]: v });

  async function run() {
    setLoading(true); setError(null);
    try { setRes(await assessCredit(req)); }
    catch (e) { setError(e instanceof Error ? e.message : "failed"); setRes(null); }
    finally { setLoading(false); }
  }

  const style = res ? DECISION_STYLE[res.decision] : null;

  return (
    <div className="mx-auto max-w-6xl px-5 py-8">
      <h1 className="text-2xl font-semibold">Loan affordability &amp; credit decision</h1>
      <p className="text-muted mt-1 max-w-3xl text-sm">
        An affordability check and a points-based scorecard combine into an auditable
        approve / refer / decline decision. Every rule that fired is returned with the result.
        This is an API-first service: the same logic is exposed at <code className="text-accent">/api/credit/assess</code>.
      </p>

      <div className="grid lg:grid-cols-[340px_1fr] gap-5 mt-6">
        <div className="card p-5 h-fit grid grid-cols-2 gap-3">
          <F label="Age"><input type="number" value={req.age} onChange={setN("age")} /></F>
          <F label="Employment type">
            <select value={req.employment_type} onChange={(e) => setV("employment_type", e.target.value)}>
              {["permanent", "contract", "self_employed", "unemployed"].map((o) =>
                <option key={o} value={o}>{o.replace("_", " ")}</option>)}
            </select>
          </F>
          <F label="Months employed"><input type="number" value={req.employment_months} onChange={setN("employment_months")} /></F>
          <F label="Existing accounts"><input type="number" value={req.existing_accounts} onChange={setN("existing_accounts")} /></F>
          <F label="Gross income /mo (R)"><input type="number" step={1000} value={req.gross_monthly_income} onChange={setN("gross_monthly_income")} /></F>
          <F label="Net income /mo (R)"><input type="number" step={1000} value={req.net_monthly_income} onChange={setN("net_monthly_income")} /></F>
          <F label="Living expenses /mo (R)"><input type="number" step={1000} value={req.monthly_living_expenses} onChange={setN("monthly_living_expenses")} /></F>
          <F label="Existing debt /mo (R)"><input type="number" step={500} value={req.existing_monthly_debt} onChange={setN("existing_monthly_debt")} /></F>
          <F label="Loan amount (R)"><input type="number" step={10000} value={req.loan_amount} onChange={setN("loan_amount")} /></F>
          <F label="Term (months)"><input type="number" value={req.term_months} onChange={setN("term_months")} /></F>
          <F label="Rate (annual %)">
            <input type="number" step={0.5} value={+(req.annual_rate * 100).toFixed(2)}
              onChange={(e) => setV("annual_rate", String(+e.target.value / 100) as unknown as string)} />
          </F>
          <F label="Adverse history">
            <select value={req.adverse_history ? "yes" : "no"} onChange={(e) => setV("adverse_history", e.target.value === "yes")}>
              <option value="no">no</option><option value="yes">yes</option>
            </select>
          </F>

          <button onClick={run} disabled={loading}
            className="col-span-2 mt-2 py-2.5 rounded-lg bg-accent text-[var(--accent-ink)] font-semibold disabled:opacity-60">
            {loading ? "Assessing…" : "Assess application"}
          </button>
          {error && <p className="col-span-2 text-warn text-xs">{error}</p>}
        </div>

        <div className="space-y-5">
          {!res && <div className="card p-10 text-center text-muted">Submit an application to see the decision and the rules behind it.</div>}
          {res && style && (
            <>
              <div className="card p-5 flex flex-wrap items-center gap-x-10 gap-y-3">
                <span className="rounded-lg px-4 py-2 text-lg font-semibold text-[var(--accent-ink)]" style={{ background: style.bg }}>
                  {style.label}
                </span>
                <Stat label="Monthly installment" value={zar(res.installment)} />
                <Stat label="Risk grade" value={`${res.scorecard.grade}  (PD ${(res.scorecard.probability_of_default * 100).toFixed(1)}%)`} />
                <Stat label="Score" value={`${res.scorecard.score}`} />
                <Stat label="Debt-to-income" value={`${(res.affordability.debt_to_income * 100).toFixed(0)}%`} />
              </div>

              <div className="grid md:grid-cols-2 gap-5">
                <div className="card p-5">
                  <h2 className="font-semibold mb-3">Affordability</h2>
                  <Row k="Disposable income /mo" v={zar(res.affordability.disposable_income)} />
                  <Row k="New installment" v={zar(res.affordability.installment)} />
                  <Row k="Total debt after loan" v={zar(res.affordability.total_debt_after)} />
                  <Row k="Installment / disposable" v={`${(res.affordability.installment_to_disposable * 100).toFixed(0)}%`} />
                  <Row k="Affordable" v={res.affordability.affordable ? "yes" : "no"} />
                </div>
                <div className="card p-5">
                  <h2 className="font-semibold mb-3">Scorecard points</h2>
                  <table className="w-full text-sm">
                    <tbody>
                      {res.scorecard.breakdown.map((b, i) => (
                        <tr key={i} className="border-b border-border/50">
                          <td className="py-1 capitalize">{b.characteristic.replace("_", " ")}</td>
                          <td className="py-1 text-muted">{String(b.value)}</td>
                          <td className="py-1 text-right font-mono" style={{ color: b.points < 0 ? "#f87171" : "var(--accent)" }}>
                            {b.points > 0 ? "+" : ""}{b.points}
                          </td>
                        </tr>
                      ))}
                      <tr className="font-semibold">
                        <td className="py-1.5" colSpan={2}>Total score</td>
                        <td className="py-1.5 text-right font-mono">{res.scorecard.score}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="card p-5">
                <h2 className="font-semibold mb-2">Decision reasons</h2>
                <ul className="space-y-1.5 text-sm">
                  {res.reasons.map((r, i) => (
                    <li key={i} className="flex gap-2"><span className="text-accent">•</span><span>{r}</span></li>
                  ))}
                </ul>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function F({ label, children }: { label: string; children: React.ReactNode }) {
  return <label className="space-y-1"><span className="field-label">{label}</span>{children}</label>;
}
function Stat({ label, value }: { label: string; value: string }) {
  return <div><div className="field-label">{label}</div><div className="text-sm font-mono">{value}</div></div>;
}
function Row({ k, v }: { k: string; v: string }) {
  return <div className="flex justify-between text-sm gap-4 py-0.5"><span className="text-muted">{k}</span><span className="font-mono">{v}</span></div>;
}
