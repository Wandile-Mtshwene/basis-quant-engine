"use client";

import { useState } from "react";
import { CashflowTable } from "./components/CashflowTable";
import { TeX } from "./components/Math";
import {
  priceLife, priceFuneral, zar, num,
  type Quote, type LifeRequest, type FuneralRequest,
} from "./lib/api";

type Product = "life" | "funeral";

const freqOptions = ["monthly", "quarterly", "semiannual", "annual"];

export default function Home() {
  const [product, setProduct] = useState<Product>("life");
  const [life, setLife] = useState<LifeRequest>({
    issue_age: 40, sex: "male", smoker_status: "nonsmoker",
    sum_assured: 1_000_000, term: 20, underwriting_class: "standard",
    frequency: "monthly", explain: true,
  });
  const [funeral, setFuneral] = useState<FuneralRequest>({
    issue_age: 65, sex: "female", sum_assured: 30_000,
    frequency: "monthly", cover_to_age: 120, explain: true,
  });
  const [quote, setQuote] = useState<Quote | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setLoading(true); setError(null);
    try {
      setQuote(product === "life" ? await priceLife(life) : await priceFuneral(funeral));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
      setQuote(null);
    } finally {
      setLoading(false);
    }
  }

  const issueAge = product === "life" ? life.issue_age : funeral.issue_age;

  return (
    <div className="mx-auto max-w-6xl px-5 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold">Life &amp; Funeral premium engine</h1>
        <p className="text-muted mt-1 max-w-3xl text-sm">
          A premium is computed server-side by a Python actuarial engine and returned with its
          complete calculation trace. Nothing is hidden: every survival probability, discount
          factor and expense loading behind the number is shown below.
        </p>
      </div>

      <div className="grid lg:grid-cols-[360px_1fr] gap-5">
        {/* ---------------- input panel ---------------- */}
        <div className="card p-5 h-fit">
          <div className="flex gap-1 p-1 rounded-lg bg-surface-2 mb-5">
            {(["life", "funeral"] as Product[]).map((p) => (
              <button
                key={p}
                onClick={() => { setProduct(p); setQuote(null); }}
                className={`flex-1 py-1.5 rounded-md text-sm capitalize transition ${
                  product === p ? "bg-accent text-[var(--accent-ink)] font-semibold" : "text-muted"
                }`}
              >
                {p}
              </button>
            ))}
          </div>

          {product === "life" ? (
            <div className="grid grid-cols-2 gap-3">
              <Field label="Issue age">
                <input type="number" min={18} max={80} value={life.issue_age}
                  onChange={(e) => setLife({ ...life, issue_age: +e.target.value })} />
              </Field>
              <Field label="Term (years)">
                <input type="number" min={1} max={50} value={life.term}
                  onChange={(e) => setLife({ ...life, term: +e.target.value })} />
              </Field>
              <Field label="Sex">
                <Select value={life.sex} opts={["male", "female"]}
                  onChange={(v) => setLife({ ...life, sex: v as LifeRequest["sex"] })} />
              </Field>
              <Field label="Smoker">
                <Select value={life.smoker_status} opts={["nonsmoker", "smoker"]}
                  onChange={(v) => setLife({ ...life, smoker_status: v as LifeRequest["smoker_status"] })} />
              </Field>
              <Field label="Sum assured (R)" full>
                <input type="number" step={50000} value={life.sum_assured}
                  onChange={(e) => setLife({ ...life, sum_assured: +e.target.value })} />
              </Field>
              <Field label="Underwriting class" full>
                <Select value={life.underwriting_class}
                  opts={["preferred", "standard", "rated_125", "rated_150", "rated_200"]}
                  onChange={(v) => setLife({ ...life, underwriting_class: v })} />
              </Field>
              <Field label="Premium frequency" full>
                <Select value={life.frequency} opts={freqOptions}
                  onChange={(v) => setLife({ ...life, frequency: v })} />
              </Field>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-3">
              <Field label="Issue age">
                <input type="number" min={0} max={85} value={funeral.issue_age}
                  onChange={(e) => setFuneral({ ...funeral, issue_age: +e.target.value })} />
              </Field>
              <Field label="Cover to age">
                <input type="number" min={90} max={120} value={funeral.cover_to_age}
                  onChange={(e) => setFuneral({ ...funeral, cover_to_age: +e.target.value })} />
              </Field>
              <Field label="Sex">
                <Select value={funeral.sex} opts={["male", "female"]}
                  onChange={(v) => setFuneral({ ...funeral, sex: v as FuneralRequest["sex"] })} />
              </Field>
              <Field label="Sum assured (R)">
                <input type="number" step={5000} value={funeral.sum_assured}
                  onChange={(e) => setFuneral({ ...funeral, sum_assured: +e.target.value })} />
              </Field>
              <Field label="Premium frequency" full>
                <Select value={funeral.frequency} opts={freqOptions}
                  onChange={(v) => setFuneral({ ...funeral, frequency: v })} />
              </Field>
            </div>
          )}

          <button
            onClick={run} disabled={loading}
            className="mt-5 w-full py-2.5 rounded-lg bg-accent text-[var(--accent-ink)] font-semibold disabled:opacity-60"
          >
            {loading ? "Pricing…" : "Calculate premium"}
          </button>
          {error && <p className="text-warn text-xs mt-3">{error} — is the API running on :8000?</p>}
        </div>

        {/* ---------------- results panel ---------------- */}
        <div className="space-y-5">
          {!quote && (
            <div className="card p-10 text-center text-muted">
              Enter the policy details and calculate a premium to see the full actuarial breakdown.
            </div>
          )}

          {quote && (
            <>
              <div className="card p-5 flex flex-wrap items-end gap-x-10 gap-y-3">
                <div>
                  <div className="field-label">Premium ({quote.frequency})</div>
                  <div className="text-4xl font-semibold text-accent">{zar(quote.premium)}</div>
                </div>
                <Stat label="Per year" value={zar(quote.annual_premium)} />
                <Stat label="Office rate /unit" value={num(quote.office_premium_rate, 6)} />
                <Stat label="Table" value={quote.table} mono={false} />
              </div>

              <div className="grid md:grid-cols-2 gap-5">
                <div className="card p-5">
                  <h2 className="font-semibold mb-3">How this premium is built</h2>
                  <ol className="space-y-2 text-sm">
                    {quote.steps.map((s) => (
                      <li key={s.step} className="flex gap-3">
                        <span className="text-muted font-mono w-5">{s.step}</span>
                        <span className="flex-1">{s.label}</span>
                        <span className="font-mono text-accent">
                          {typeof s.value === "number" ? num(s.value, 6) : s.value}
                        </span>
                      </li>
                    ))}
                  </ol>
                </div>

                <div className="card p-5">
                  <h2 className="font-semibold mb-3">The formulas</h2>
                  <div className="text-sm space-y-3 text-muted">
                    <div>
                      <p className="mb-1 text-foreground">EPV of benefits</p>
                      <TeX block>{product === "life"
                        ? "A = \\sum_{t=0}^{n-1} v^{t+1}\\; {}_{t}p_x\\; q_{x+t}"
                        : "A_x = \\sum_{t=0}^{\\omega-x-1} v^{t+0.5}\\; {}_{t}p_x\\; q_{x+t}"}</TeX>
                    </div>
                    <div>
                      <p className="mb-1 text-foreground">Premium annuity-due</p>
                      <TeX block>{"\\ddot a_{x:\\overline{n}|} = \\sum_{t=0}^{n-1} v^{t}\\; {}_{t}p_x"}</TeX>
                    </div>
                    <div>
                      <p className="mb-1 text-foreground">Gross (office) premium</p>
                      <TeX block>{"G = \\dfrac{S\\cdot A + I + e_{\\infty}\\,\\ddot a}{\\ddot a\\,(1-r-c)}"}</TeX>
                    </div>
                    <p className="text-xs">
                      i = {quote.trace ? num(quote.trace.interest_rate, 4) : "—"}, v = 1/(1+i).
                      S sum assured, I initial expense, r renewal %, c commission %.
                    </p>
                  </div>
                </div>
              </div>

              {quote.trace && (
                <div className="card p-5">
                  <h2 className="font-semibold mb-1">Year-by-year expected discounted cashflows</h2>
                  <p className="text-muted text-sm mb-3">
                    Each row is a policy year. The EPV contributions sum to A, the exact number used in the premium.
                  </p>
                  <CashflowTable trace={quote.trace.benefits} issueAge={issueAge} />
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function Field({ label, children, full }: { label: string; children: React.ReactNode; full?: boolean }) {
  return (
    <label className={`space-y-1 ${full ? "col-span-2" : ""}`}>
      <span className="field-label">{label}</span>
      {children}
    </label>
  );
}

function Select({ value, opts, onChange }: { value: string; opts: string[]; onChange: (v: string) => void }) {
  return (
    <select value={value} onChange={(e) => onChange(e.target.value)}>
      {opts.map((o) => <option key={o} value={o}>{o.replace("_", " ")}</option>)}
    </select>
  );
}

function Stat({ label, value, mono = true }: { label: string; value: string; mono?: boolean }) {
  return (
    <div>
      <div className="field-label">{label}</div>
      <div className={`text-sm ${mono ? "font-mono" : ""}`}>{value}</div>
    </div>
  );
}
