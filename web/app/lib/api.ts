// Resolve the pricing API base URL:
// - explicit override via NEXT_PUBLIC_API_URL wins
// - deployed (any non-local host): same-origin, requests hit the Python
//   serverless function mounted at /api
// - local dev: the FastAPI dev server on :8000
const RAW = process.env.NEXT_PUBLIC_API_URL;
function resolveBase(): string {
  if (RAW !== undefined) return RAW.replace(/\/$/, "");
  if (typeof window !== "undefined") {
    const h = window.location.hostname;
    if (h !== "localhost" && h !== "127.0.0.1") return ""; // same-origin
  }
  return "http://127.0.0.1:8000";
}
export const API_URL = resolveBase();

export type Step = { step: number; label: string; value: number | string };

export type AssuranceTrace = {
  epv: number;
  years: number[];
  survival: number[];
  death_prob: number[];
  discount: number[];
  expected_discounted: number[];
};

export type Quote = {
  product: string;
  premium: number;
  frequency: string;
  annual_premium: number;
  net_premium_rate: number;
  office_premium_rate: number;
  epv_benefits: number;
  annuity: number;
  table: string;
  inputs: Record<string, unknown>;
  steps: Step[];
  trace?: {
    interest_rate: number;
    expense_loading: Record<string, number>;
    benefits: AssuranceTrace;
    annuity: AssuranceTrace & { frequency: number; frequency_adjustment: number };
  };
};

export type LifeRequest = {
  issue_age: number;
  sex: "male" | "female";
  smoker_status: "nonsmoker" | "smoker";
  sum_assured: number;
  term: number;
  underwriting_class: string;
  frequency: string;
  explain: boolean;
};

export type FuneralRequest = {
  issue_age: number;
  sex: "male" | "female";
  sum_assured: number;
  frequency: string;
  cover_to_age: number;
  explain: boolean;
};

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`);
  return res.json();
}

export const priceLife = (req: LifeRequest) => post<Quote>("/api/price/life", req);
export const priceFuneral = (req: FuneralRequest) => post<Quote>("/api/price/funeral", req);

export type RetirementRequest = {
  current_age: number;
  retirement_age: number;
  end_age: number;
  current_savings: number;
  annual_contribution: number;
  contribution_escalation: number;
  expected_return: number;
  return_volatility: number;
  inflation: number;
  target_income: number;
  n_sims: number;
};

export type RetirementProjection = {
  ages: number[];
  percentiles: Record<"p5" | "p25" | "p50" | "p75" | "p95", number[]>;
  capital_at_retirement: Record<"p5" | "p25" | "p50" | "p75" | "p95", number>;
  success_probability: number;
  probability_of_ruin: number;
  median_depletion_age: number | null;
  target_income_first_year: number;
  inputs: Record<string, number>;
  n_sims: number;
};

export const projectRetirement = (req: RetirementRequest) =>
  post<RetirementProjection>("/api/retirement/project", req);

export async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`);
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}

export const zar = (n: number) =>
  new Intl.NumberFormat("en-ZA", { style: "currency", currency: "ZAR", maximumFractionDigits: 2 }).format(n);
export const num = (n: number, d = 6) =>
  n.toLocaleString("en-ZA", { maximumFractionDigits: d, minimumFractionDigits: 0 });
