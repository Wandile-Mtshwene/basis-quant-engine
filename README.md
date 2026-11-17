# Basis — Life & Funeral Premium Engine

An open-core actuarial pricing engine for **level term life assurance** and
**whole-of-life funeral cover**, built on **real public mortality tables** and
wrapped in a transparent API and UI. Every premium can be returned with its
complete calculation trace, so nothing is a black box.

This is the flagship of a small portfolio demonstrating the full path an
actuarial/quant developer owns: the mathematics, a tested engine, a documented
API, a usable interface, and the same calculation reproduced independently in
Excel.

```
 Next.js UI  ──HTTP──▶  FastAPI (/api)  ──▶  basis  (pure-Python engine)
  (quote + admin)        explain mode         mortality · EPVs · pricing
                                                      │
                                              real SOA / ELT tables
```

## Why it is credible

- **Real tables, not toys.** Life pricing uses the **2015 VBT** smoker-distinct
  select & ultimate tables (male/female × smoker/non-smoker); funeral uses the
  **ELT No. 15 (1990-92)** population life tables (full age span). Both are
  public and are pulled from the SOA table library via `pymort`
  (`scripts/vendor_tables.py`) and vendored as CSV.
- **Proven correct.** The engine is validated against closed-form benchmarks —
  e.g. with flat mortality the net premium collapses to `q / (1 + i)`, and the
  identity `A_x = 1 − d·ä_x` holds exactly on a closed table.
- **Proven twice.** An Excel workbook (`excel/`) reproduces the life calculation
  with *live formulas*; a test evaluates that workbook with an independent
  formula engine and checks it lands on the same premium to the cent.

## The actuarial maths

Per unit sum assured, with `v = 1/(1+i)` and `ₜpₓ` the survival probability:

| Quantity | Formula |
| --- | --- |
| Term assurance EPV | `A¹ₓ:ₙ = Σ vᵗ⁺¹ · ₜpₓ · q₍ₓ₊ₜ₎` |
| Whole-of-life EPV (funeral, mid-year) | `Aₓ = Σ vᵗ⁺⁰·⁵ · ₜpₓ · q₍ₓ₊ₜ₎` |
| Premium annuity-due | `äₓ:ₙ = Σ vᵗ · ₜpₓ` (with the UDD m-thly adjustment) |
| Net premium | `Pⁿᵉᵗ = S · A / ä` |
| Gross (office) premium | `G = (S·A + I + e∞·ä) / (ä·(1 − r − c))` |

### Rating factors (life)
Age, sex and smoker status (select the base table); **underwriting class**
(mortality multiplier, 0.85×–2.0×); **sum-assured band** (premium discount);
**premium frequency** (drives the m-thly annuity adjustment). Funeral cover is
whole-of-life, mid-year benefit, and is not smoker- or underwriting-rated.

All assumptions live in `src/basis/assumptions.py` and are served at
`/api/assumptions` — the admin view renders them so the whole rate book is
visible in one place.

## Repository layout

```
src/basis/            the open-core engine (MIT)
  mortality.py        select&ultimate + aggregate tables, one interface
  actuarial.py        assurance & annuity EPVs, each returning a full trace
  assumptions.py      interest, expense and rating-factor basis (inspectable)
  pricing.py          price_life / price_funeral -> itemised Quote
  data/               real vendored mortality tables (CSV)
api/main.py           FastAPI service, everything under /api, explain mode
web/                  Next.js UI: quote page, admin rate book, KaTeX formulas
excel/build_model.py  generates the live-formula Excel parallel model
tests/                55+ tests: benchmarks, rating-factor ordering, API, Excel
scripts/              table vendoring + web bundling for deploy
```

## Running it locally

```bash
# 1. Python engine + API (terminal 1)
uv sync
uv run uvicorn api.main:app --reload          # http://127.0.0.1:8000/api/docs

# 2. Web UI (terminal 2)
cd web && npm install && npm run dev           # http://localhost:3000

# tests
uv run pytest -q

# regenerate the Excel model
uv run python excel/build_model.py             # -> excel/Life_Premium_Model.xlsx
```

## Deploying

The web app and the Python engine deploy as **one Vercel project**: the engine
is bundled next to a serverless entrypoint and mounted at `/api`.

```bash
uv run python scripts/vendor_web.py            # bundle engine into web/api
cd web && vercel --prod
```

## Data & licensing note

Tables are public SOA / ELT datasets used for demonstration; this is an
illustrative pricing basis, not any insurer's rate book. SA85-90 or an insurer's
own table can be dropped in — the engine is table-agnostic.
