"""Generate a synthetic mortality-experience dataset for the studio.

Exposure and observed deaths are simulated off the real 2015 VBT expected basis
with a KNOWN set of A/E distortions, so the analysis can be checked: the studio
should recover ~105% overall, heavier smoker and older-age experience, and
slightly lighter female experience.

    uv run python scripts/generate_experience.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from basis.experience import expected_qx

OUT = Path(__file__).resolve().parents[1] / "src" / "basis" / "data" / "experience"

# True A/E distortions baked into the simulated world.
BASE = 1.05
SMOKER_EXTRA = 1.12
OLD_AGE_EXTRA = 1.08     # applied from age 60
FEMALE_FACTOR = 0.97


def true_factor(age: int, sex: str, smoker: str) -> float:
    f = BASE
    if smoker == "smoker":
        f *= SMOKER_EXTRA
    if age >= 60:
        f *= OLD_AGE_EXTRA
    if sex == "female":
        f *= FEMALE_FACTOR
    return f


def main() -> None:
    rng = np.random.default_rng(2026)
    rows = []
    for age in range(25, 81, 5):
        for sex in ("male", "female"):
            for smoker in ("nonsmoker", "smoker"):
                exposure = float(rng.integers(800, 4000))
                q_exp = expected_qx(age, sex, smoker)
                true_q = q_exp * true_factor(age, sex, smoker)
                actual = int(rng.poisson(exposure * true_q))
                rows.append({
                    "age": age, "sex": sex, "smoker_status": smoker,
                    "exposure": exposure, "actual_deaths": actual,
                })
    df = pd.DataFrame(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT / "mortality_experience.csv", index=False)
    tot_exp = df["exposure"].sum()
    print(f"Wrote {len(df)} cells, {tot_exp:,.0f} life-years, "
          f"{df['actual_deaths'].sum()} deaths -> {OUT}")


if __name__ == "__main__":
    main()
