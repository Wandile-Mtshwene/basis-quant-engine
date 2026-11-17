"use client";

import { useState } from "react";
import { ValueCurve } from "../components/ValueCurve";
import { priceOption, num, type OptionRequest, type OptionResult } from "../lib/api";

const DEFAULTS: OptionRequest = {
  S: 100, K: 100, T: 1, r: 0.05, sigma: 0.20, q: 0.0, option_type: "call", n_sims: 100_000,
};

export default function Options() {
  const [req, setReq] = useState<OptionRequest>(DEFAULTS);
  const [res, setRes] = useState<OptionResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const setN = (k: keyof OptionRequest) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setReq({ ...req, [k]: +e.target.value });
  const setPct = (k: keyof OptionRequest) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setReq({ ...req, [k]: +e.target.value / 100 });

  async function run() {
    setLoading(true); setError(null);
    try { setRes(await priceOption(req)); }
    catch (e) { setError(e instanceof Error ? e.message : "failed"); setRes(null); }
    finally { setLoading(false); }
  }

  const mcGap = res ? Math.abs(res.monte_carlo.price - res.price) : 0;

  return (
    <div className="mx-auto max-w-6xl px-5 py-8">
      <h1 className="text-2xl font-semibold">Options pricing &amp; risk toolkit</h1>
      <p className="text-muted mt-1 max-w-3xl text-sm">
        European option pricing by Black-Scholes, with the full Greeks, a Monte Carlo cross-check and
        put-call parity. The closed-form price and the simulated price agree within Monte Carlo error.
      </p>

      <div className="grid lg:grid-cols-[300px_1fr] gap-5 mt-6">
        <div className="card p-5 h-fit grid grid-cols-2 gap-3">
          <div className="col-span-2 flex gap-1 p-1 rounded-lg bg-surface-2">
            {(["call", "put"] as const).map((t) => (
              <button key={t} onClick={() => setReq({ ...req, option_type: t })}
                className={`flex-1 py-1.5 rounded-md text-sm capitalize ${
                  req.option_type === t ? "bg-accent text-[var(--accent-ink)] font-semibold" : "text-muted"}`}>
                {t}
              </button>
            ))}
          </div>
          <F label="Spot S"><input type="number" value={req.S} onChange={setN("S")} /></F>
          <F label="Strike K"><input type="number" value={req.K} onChange={setN("K")} /></F>
          <F label="Expiry T (years)"><input type="number" step={0.25} value={req.T} onChange={setN("T")} /></F>
          <F label="Simulations"><input type="number" step={10000} value={req.n_sims} onChange={setN("n_sims")} /></F>
          <F label="Volatility σ (%)"><input type="number" step={1} value={+(req.sigma * 100).toFixed(2)} onChange={setPct("sigma")} /></F>
          <F label="Rate r (%)"><input type="number" step={0.25} value={+(req.r * 100).toFixed(2)} onChange={setPct("r")} /></F>
          <F label="Dividend q (%)"><input type="number" step={0.25} value={+(req.q * 100).toFixed(2)} onChange={setPct("q")} /></F>

          <button onClick={run} disabled={loading}
            className="col-span-2 mt-2 py-2.5 rounded-lg bg-accent text-[var(--accent-ink)] font-semibold disabled:opacity-60">
            {loading ? "Pricing…" : "Price option"}
          </button>
          {error && <p className="col-span-2 text-warn text-xs">{error}</p>}
        </div>

        <div className="space-y-5">
          {!res && <div className="card p-10 text-center text-muted">Set the contract and price it to see the value, Greeks and Monte Carlo check.</div>}
          {res && (
            <>
              <div className="card p-5 flex flex-wrap items-end gap-x-10 gap-y-3">
                <div>
                  <div className="field-label">{res.option_type} price (Black-Scholes)</div>
                  <div className="text-4xl font-semibold text-accent">{res.price.toFixed(4)}</div>
                </div>
                <Stat label="Monte Carlo" value={`${res.monte_carlo.price.toFixed(4)} ± ${res.monte_carlo.std_error.toFixed(4)}`} />
                <Stat label="BS vs MC gap" value={mcGap.toFixed(4)} />
                <Stat label="Parity residual" value={num(res.put_call_parity.residual, 8)} />
                <Stat label="d1 / d2" value={`${res.d1.toFixed(4)} / ${res.d2.toFixed(4)}`} />
              </div>

              <div className="grid md:grid-cols-[1fr_260px] gap-5">
                <div className="card p-5">
                  <h2 className="font-semibold mb-2">Value vs spot</h2>
                  <ValueCurve res={res} strike={req.K} spot={req.S} />
                  <div className="flex gap-4 text-xs text-muted mt-1">
                    <span className="inline-flex items-center gap-1"><i className="w-4 h-0.5 inline-block" style={{ background: "var(--accent)" }} />option value</span>
                    <span className="inline-flex items-center gap-1"><i className="w-4 h-0.5 inline-block border-t border-dashed" style={{ borderColor: "var(--muted)" }} />intrinsic payoff</span>
                  </div>
                </div>
                <div className="card p-5">
                  <h2 className="font-semibold mb-3">Greeks</h2>
                  <G k="Delta" v={res.greeks.delta} />
                  <G k="Gamma" v={res.greeks.gamma} />
                  <G k="Vega (per 1% vol)" v={res.greeks.vega_per_1pct} />
                  <G k="Theta (per day)" v={res.greeks.theta_per_day} />
                  <G k="Rho (per 1% rate)" v={res.greeks.rho_per_1pct} />
                </div>
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
function G({ k, v }: { k: string; v: number }) {
  return <div className="flex justify-between text-sm py-0.5"><span className="text-muted">{k}</span><span className="font-mono">{v.toFixed(5)}</span></div>;
}
