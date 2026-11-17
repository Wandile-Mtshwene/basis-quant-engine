"use client";

import { useEffect, useState } from "react";
import { TeX } from "../components/Math";
import { getJSON, num } from "../lib/api";

type Assumptions = {
  interest_rate: number;
  expenses: {
    initial_fixed: number; initial_per_mille: number; policy_fee: number;
    renewal_pct: number; commission_pct: number;
  };
  rating: {
    underwriting_class: Record<string, number>;
    sum_assured_bands: { from: number; to: number; multiplier: number }[];
    frequency: Record<string, number>;
  };
};

type Tables = {
  life: { sex: string; smoker_status: string; name: string; select_period: number; sample_q: Record<string, number> }[];
  funeral: { sex: string; name: string; min_age: number; max_age: number; sample_q: Record<string, number> }[];
};

export default function Admin() {
  const [a, setA] = useState<Assumptions | null>(null);
  const [t, setT] = useState<Tables | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([getJSON<Assumptions>("/api/assumptions"), getJSON<Tables>("/api/tables")])
      .then(([aa, tt]) => { setA(aa); setT(tt); })
      .catch((e) => setErr(e instanceof Error ? e.message : "load failed"));
  }, []);

  if (err) return <Shell><p className="text-warn">{err} — start the API on :8000.</p></Shell>;
  if (!a || !t) return <Shell><p className="text-muted">Loading basis…</p></Shell>;

  return (
    <Shell>
      <h1 className="text-2xl font-semibold">Pricing basis &amp; rate book</h1>
      <p className="text-muted text-sm mt-1 mb-6 max-w-3xl">
        Every number the engine prices from, in one place and served live from the API. This is the
        single source of truth: change it here (in the engine) and every quote moves with it.
      </p>

      <div className="grid md:grid-cols-2 gap-5">
        <Card title="Valuation basis">
          <Row k="Pricing interest rate i" v={`${(a.interest_rate * 100).toFixed(2)}%`} />
          <Row k="One-year discount v = 1/(1+i)" v={num(1 / (1 + a.interest_rate), 6)} />
        </Card>

        <Card title="Expense & commission loadings">
          <Row k="Initial fixed expense" v={`R ${a.expenses.initial_fixed}`} />
          <Row k="Initial expense per R1,000 SA" v={`R ${a.expenses.initial_per_mille}`} />
          <Row k="Policy fee (each year)" v={`R ${a.expenses.policy_fee}`} />
          <Row k="Renewal expense" v={`${(a.expenses.renewal_pct * 100).toFixed(1)}% of premium`} />
          <Row k="Commission" v={`${(a.expenses.commission_pct * 100).toFixed(1)}% of premium`} />
        </Card>

        <Card title="Underwriting class — mortality multiplier">
          {Object.entries(a.rating.underwriting_class).map(([k, v]) => (
            <Row key={k} k={k.replace("_", " ")} v={`× ${v.toFixed(2)}`} />
          ))}
        </Card>

        <Card title="Sum-assured band — premium multiplier">
          {a.rating.sum_assured_bands.map((b, i) => (
            <Row key={i}
              k={`R ${b.from.toLocaleString()} – ${b.to === null || !isFinite(b.to) ? "∞" : "R " + b.to.toLocaleString()}`}
              v={`× ${b.multiplier.toFixed(2)}`} />
          ))}
        </Card>

        <Card title="Premium frequency — payments / year">
          {Object.entries(a.rating.frequency).map(([k, v]) => (
            <Row key={k} k={k} v={`${v}`} />
          ))}
        </Card>

        <Card title="Pricing formulas">
          <div className="space-y-2 text-sm text-muted">
            <TeX block>{"A^{1}_{x:\\overline{n}|} = \\sum_{t=0}^{n-1} v^{t+1}\\,{}_{t}p_x\\,q_{x+t}"}</TeX>
            <TeX block>{"\\ddot a_{x:\\overline{n}|} = \\sum_{t=0}^{n-1} v^{t}\\,{}_{t}p_x"}</TeX>
            <TeX block>{"P^{net} = S\\cdot A / \\ddot a"}</TeX>
            <TeX block>{"G = \\dfrac{S\\,A + I + e_\\infty\\,\\ddot a}{\\ddot a\\,(1-r-c)}"}</TeX>
          </div>
        </Card>
      </div>

      <h2 className="text-lg font-semibold mt-8 mb-3">Mortality tables (sample rates qₓ)</h2>
      <div className="grid md:grid-cols-2 gap-5">
        <Card title="Life — 2015 VBT, Select &amp; Ultimate">
          <table className="w-full text-sm">
            <thead className="text-muted text-left">
              <tr><th className="py-1">Table</th><th>q30</th><th>q40</th><th>q50</th><th>q60</th><th>q70</th></tr>
            </thead>
            <tbody className="font-mono">
              {t.life.map((r) => (
                <tr key={r.name} className="border-t border-border/60">
                  <td className="py-1 pr-2 font-sans">{r.sex} {r.smoker_status}</td>
                  {["30", "40", "50", "60", "70"].map((age) => (
                    <td key={age}>{num(r.sample_q[age], 5)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          <p className="text-xs text-muted mt-2">Select period {t.life[0].select_period} years. Smoker and sex select the table; underwriting class scales it.</p>
        </Card>

        <Card title="Funeral — ELT No. 15 (1990-92)">
          <table className="w-full text-sm">
            <thead className="text-muted text-left">
              <tr><th className="py-1">Table</th><th>Age span</th><th>q30</th><th>q50</th><th>q70</th><th>q90</th></tr>
            </thead>
            <tbody className="font-mono">
              {t.funeral.map((r) => (
                <tr key={r.name} className="border-t border-border/60">
                  <td className="py-1 pr-2 font-sans">{r.sex}</td>
                  <td>{r.min_age}–{r.max_age}</td>
                  {["30", "50", "70", "90"].map((age) => (
                    <td key={age}>{num(r.sample_q[age], 5)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          <p className="text-xs text-muted mt-2">Full population life table spanning all ages, used for whole-of-life funeral cover.</p>
        </Card>
      </div>
    </Shell>
  );
}

function Shell({ children }: { children: React.ReactNode }) {
  return <div className="mx-auto max-w-6xl px-5 py-8">{children}</div>;
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="card p-5">
      <h3 className="font-semibold mb-3" dangerouslySetInnerHTML={{ __html: title }} />
      <div className="space-y-1.5">{children}</div>
    </div>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex justify-between text-sm gap-4">
      <span className="text-muted">{k}</span>
      <span className="font-mono">{v}</span>
    </div>
  );
}
