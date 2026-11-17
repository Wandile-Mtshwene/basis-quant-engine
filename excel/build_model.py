"""Generate an Excel workbook that reproduces the Life premium calculation with
LIVE Excel formulas (not pasted values), driven off the same real mortality
table the Python engine uses.

The point is to show the identical actuarial calculation expressed in a second,
independent medium: open the file in Excel and every cell recomputes.  The
companion test (tests/test_excel.py) proves the workbook's methodology lands on
the same premium as the engine.

    uv run python excel/build_model.py            # -> excel/Life_Premium_Model.xlsx
"""

from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from basis.assumptions import DEFAULT_BASIS
from basis.mortality import load_vbt

OUT = Path(__file__).resolve().parent / "Life_Premium_Model.xlsx"

# The scenario the workbook is built for (mirrors the engine's default demo).
SCENARIO = dict(
    issue_age=40, sex="male", smoker_status="nonsmoker",
    sum_assured=1_000_000, term=20, underwriting_class="standard", frequency="monthly",
)

HEAD = Font(bold=True, color="FFFFFF")
HEAD_FILL = PatternFill("solid", fgColor="0E7C6B")
TITLE = Font(bold=True, size=13)
SUB = Font(bold=True, size=11, color="0E7C6B")
MONEY = "#,##0.00"
RATE = "0.000000"
THIN = Side(style="thin", color="D0D7E2")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def build() -> Path:
    basis = DEFAULT_BASIS
    s = SCENARIO
    table = load_vbt(s["sex"], s["smoker_status"])
    n = s["term"]
    uw_mult = basis.rating.underwriting_multiplier(s["underwriting_class"])
    sa_mult = basis.rating.sum_assured_multiplier(s["sum_assured"])
    m = basis.rating.frequency_payments(s["frequency"])

    wb = Workbook()

    # ---------------- Inputs sheet (named cells drive everything) ----------- #
    ins = wb.active
    ins.title = "Inputs"
    ins["A1"] = "Life premium model — inputs & basis"
    ins["A1"].font = TITLE
    rows = [
        ("Issue age", s["issue_age"], "issue_age"),
        ("Term (years)", n, "term"),
        ("Sex", s["sex"], None),
        ("Smoker status", s["smoker_status"], None),
        ("Underwriting class", s["underwriting_class"], None),
        ("Sum assured", s["sum_assured"], "sum_assured"),
        ("Interest rate i", basis.interest_rate, "i"),
        ("Discount v = 1/(1+i)", "=1/(1+i)", "v"),
        ("Underwriting mortality multiplier", uw_mult, "uw_mult"),
        ("Sum-assured band multiplier", sa_mult, "sa_mult"),
        ("Payments per year m", m, "m"),
        ("Initial fixed expense", basis.expenses.initial_fixed, "init_fixed"),
        ("Initial expense per R1,000 SA", basis.expenses.initial_per_mille, "init_mille"),
        ("Policy fee per year", basis.expenses.policy_fee, "policy_fee"),
        ("Renewal expense %", basis.expenses.renewal_pct, "renewal"),
        ("Commission %", basis.expenses.commission_pct, "commission"),
    ]
    for r, (label, value, name) in enumerate(rows, start=3):
        ins.cell(r, 1, label).font = Font(bold=True)
        c = ins.cell(r, 2, value)
        if isinstance(value, float) and value < 1:
            c.number_format = RATE
        if name:
            wb.defined_names.add(_defined(name, f"Inputs!$B${r}"))
    ins.column_dimensions["A"].width = 34
    ins.column_dimensions["B"].width = 16

    # ---------------- Mortality sheet (real table data) --------------------- #
    mort = wb.create_sheet("Mortality")
    mort["A1"] = f"Base mortality qx — {table.name}"
    mort["A1"].font = SUB
    for j, h in enumerate(["Policy year", "Attained age", "Base qx (table)"], start=1):
        cell = mort.cell(3, j, h)
        cell.font = HEAD; cell.fill = HEAD_FILL
    for t in range(1, n + 1):
        mort.cell(3 + t, 1, t)
        mort.cell(3 + t, 2, s["issue_age"] + t - 1)
        mort.cell(3 + t, 3, round(table.q(s["issue_age"], t), 8)).number_format = "0.00000000"
    mort.column_dimensions["A"].width = 12
    mort.column_dimensions["B"].width = 14
    mort.column_dimensions["C"].width = 16

    # ---------------- Calculation sheet (LIVE formulas) --------------------- #
    calc = wb.create_sheet("Calculation")
    calc["A1"] = "Expected present values — computed live"
    calc["A1"].font = SUB
    headers = ["t", "Attained age", "q (rated)", "ₜ₋₁pₓ survival", "v^t",
               "P(death yr)", "EPV benefit", "v^(t-1)", "EPV annuity"]
    for j, h in enumerate(headers, start=1):
        cell = calc.cell(3, j, h)
        cell.font = HEAD; cell.fill = HEAD_FILL; cell.alignment = Alignment(horizontal="center")

    first, last = 4, 3 + n
    for t in range(1, n + 1):
        row = 3 + t
        mrow = 3 + t  # matching Mortality row
        calc.cell(row, 1, t)
        calc.cell(row, 2, f"=Mortality!B{mrow}")
        # rated q = min(1, base * uw multiplier)
        calc.cell(row, 3, f"=MIN(1,Mortality!C{mrow}*uw_mult)").number_format = "0.00000000"
        # survival to START of year t:  year 1 = 1; else prev_survival*(1-prev_q)
        if t == 1:
            calc.cell(row, 4, 1).number_format = RATE
        else:
            calc.cell(row, 4, f"=D{row-1}*(1-C{row-1})").number_format = RATE
        calc.cell(row, 5, f"=v^{t}").number_format = RATE                     # v^t (end-year benefit)
        calc.cell(row, 6, f"=D{row}*C{row}").number_format = "0.00000000"     # death prob
        calc.cell(row, 7, f"=E{row}*F{row}").number_format = "0.00000000"     # EPV benefit
        calc.cell(row, 8, f"=v^{t-1}").number_format = RATE                   # v^(t-1)
        calc.cell(row, 9, f"=H{row}*D{row}").number_format = RATE             # EPV annuity
        for col in range(1, 10):
            calc.cell(row, col).border = BORDER

    # totals
    tot = last + 1
    calc.cell(tot, 6, "Totals:").font = Font(bold=True)
    a_cell = f"G{tot}"
    calc.cell(tot, 7, f"=SUM(G{first}:G{last})").font = Font(bold=True)       # A (EPV benefits)
    annuity_annual = f"I{tot}"
    calc.cell(tot, 9, f"=SUM(I{first}:I{last})").font = Font(bold=True)       # ä annual
    for c in ("G", "I"):
        calc[f"{c}{tot}"].number_format = RATE
    # npx (survival to end of term) for the m-thly adjustment
    calc.cell(tot + 1, 8, "npx:").font = Font(bold=True)
    npx_cell = f"I{tot+1}"
    calc.cell(tot + 1, 9, f"=D{last}*(1-C{last})").number_format = RATE
    for w, col in zip((5, 14, 12, 12, 10, 12, 12, 10, 12), "ABCDEFGHI"):
        calc.column_dimensions[col].width = w

    # ---------------- Premium sheet (ties it together) --------------------- #
    prem = wb.create_sheet("Premium")
    prem["A1"] = "Premium build-up"
    prem["A1"].font = TITLE
    A = f"Calculation!{a_cell}"
    aa = f"Calculation!{annuity_annual}"
    npx = f"Calculation!{npx_cell}"
    lines = [
        ("EPV of benefits  A", f"={A}", RATE),
        ("Annuity-due annual  ä", f"={aa}", RATE),
        ("m-thly adjustment  (m-1)/(2m)·(1 - v^n·npx)",
         f"=(m-1)/(2*m)*(1 - v^term*{npx})", RATE),
        ("Annuity-due adjusted  ä⁽ᵐ⁾", "=B4-B5", RATE),
        ("Net premium rate  A / ä⁽ᵐ⁾", "=B3/B6", RATE),
        ("EPV claims  S·A", "=sum_assured*B3", MONEY),
        ("EPV initial expenses  I", "=init_fixed+init_mille*sum_assured/1000", MONEY),
        ("EPV policy fee  e∞·ä⁽ᵐ⁾", "=policy_fee*B6", MONEY),
        ("Loadable fraction  (1 - r - c)", "=1-renewal-commission", RATE),
        ("Gross annual premium  G (before band)", "=(B8+B9+B10)/(B6*B11)", MONEY),
        ("Gross annual premium  G (after band)", "=B12*sa_mult", MONEY),
        ("Premium per period  G/m", "=B13/m", MONEY),
    ]
    for r, (label, formula, fmt) in enumerate(lines, start=3):
        prem.cell(r, 1, label).font = Font(bold=(r in (5, 13, 15)))
        c = prem.cell(r, 2, formula)
        c.number_format = fmt
        c.font = Font(bold=(r in (5, 13, 15)))
    prem.cell(15, 1).value = "MONTHLY PREMIUM"
    prem.cell(15, 2).fill = PatternFill("solid", fgColor="D1FAE5")
    prem.column_dimensions["A"].width = 42
    prem.column_dimensions["B"].width = 18

    # Force Excel/LibreOffice to recalculate every formula on open.
    wb.calculation.fullCalcOnLoad = True
    wb.save(OUT)
    return OUT


def _defined(name: str, ref: str):
    from openpyxl.workbook.defined_name import DefinedName
    return DefinedName(name, attr_text=ref)


if __name__ == "__main__":
    path = build()
    print("Wrote", path)
