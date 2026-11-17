"""Mortality tables and survival probabilities.

Two table shapes are supported, both loaded from real public data vendored
under ``basis/data`` (see ``scripts/vendor_tables.py``):

* :class:`SelectUltimateTable` - a select & ultimate table (e.g. 2015 VBT).
  Mortality depends on *issue age* and *policy duration* during the select
  period, then on *attained age* in the ultimate period.
* :class:`AggregateTable` - a one-dimensional table keyed on attained age
  only (e.g. an English Life Table used for funeral whole-of-life cover).

Both expose the same interface via :class:`MortalityTable`::

    q(issue_age, policy_year)   # mortality rate in a given policy year (1-based)
    survival_curve(issue_age, n)  # [1, p0, 2p0, ...] length n+1

so the pricing engine never needs to know which kind of table it is holding.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from importlib.resources import files

import numpy as np
import pandas as pd

_DATA = files("basis.data")

# Rating factor -> vendored table label. Smoker status and sex select the table;
# relative-risk / underwriting class is applied as a multiplier (see pricing).
_VBT_LABELS = {
    ("male", "nonsmoker"): "male_ns",
    ("male", "smoker"): "male_sm",
    ("female", "nonsmoker"): "female_ns",
    ("female", "smoker"): "female_sm",
}
_ELT_LABELS = {"male": "male", "female": "female"}


class MortalityTable:
    """Common interface for all mortality tables."""

    name: str

    def q(self, issue_age: int, policy_year: int) -> float:
        """Mortality rate q applying in ``policy_year`` (1 = first year of cover)
        for a life who took out the policy at ``issue_age``."""
        raise NotImplementedError

    def survival_curve(self, issue_age: int, n: int) -> np.ndarray:
        """``t`` -> probability of surviving the first ``t`` policy years,
        for ``t`` in ``0..n``.  Element 0 is always 1.0."""
        p = np.empty(n + 1)
        p[0] = 1.0
        for t in range(1, n + 1):
            p[t] = p[t - 1] * (1.0 - self.q(issue_age, t))
        return p

    def q_vector(self, issue_age: int, n: int) -> np.ndarray:
        """Mortality rates for policy years ``1..n``."""
        return np.array([self.q(issue_age, t) for t in range(1, n + 1)])


@dataclass
class AggregateTable(MortalityTable):
    """One-dimensional table: mortality depends only on attained age."""

    name: str
    _qx: np.ndarray  # index = attained age
    min_age: int = 0

    @property
    def max_age(self) -> int:
        return self.min_age + len(self._qx) - 1

    def qx(self, age: int) -> float:
        """Raw mortality rate at an attained age (clamped to table range)."""
        i = min(max(age, self.min_age), self.max_age) - self.min_age
        return float(self._qx[i])

    def q(self, issue_age: int, policy_year: int) -> float:
        return self.qx(issue_age + policy_year - 1)


@dataclass
class SelectUltimateTable(MortalityTable):
    """Select & ultimate table.  During the first ``select_period`` policy years
    mortality depends on issue age and duration; thereafter on attained age."""

    name: str
    _select: dict[tuple[int, int], float]  # (issue_age, duration) -> q
    _ult: np.ndarray                        # index = attained age - ult_min_age
    ult_min_age: int
    select_period: int

    @property
    def ult_max_age(self) -> int:
        return self.ult_min_age + len(self._ult) - 1

    def _q_ult(self, age: int) -> float:
        i = min(max(age, self.ult_min_age), self.ult_max_age) - self.ult_min_age
        return float(self._ult[i])

    def ultimate_qx(self, age: int) -> float:
        """Ultimate mortality rate at an attained age - a convenient population
        basis for experience analysis, independent of policy duration."""
        return self._q_ult(age)

    def q(self, issue_age: int, policy_year: int) -> float:
        if policy_year <= self.select_period:
            key = (issue_age, policy_year)
            if key in self._select:
                return self._select[key]
        # fall through to ultimate on attained age
        return self._q_ult(issue_age + policy_year - 1)


# --------------------------------------------------------------------------- #
# Loaders (cached so repeated pricing calls do not re-read the CSVs)
# --------------------------------------------------------------------------- #
@lru_cache(maxsize=None)
def load_vbt(sex: str, smoker_status: str) -> SelectUltimateTable:
    """Load a 2015 VBT smoker-distinct select & ultimate table."""
    label = _VBT_LABELS[(sex, smoker_status)]
    sel_df = pd.read_csv(_DATA / "vbt" / f"{label}.select.csv")
    ult_df = pd.read_csv(_DATA / "vbt" / f"{label}.ult.csv")

    select = {
        (int(r.issue_age), int(r.duration)): float(r.qx)
        for r in sel_df.itertuples(index=False)
    }
    select_period = int(sel_df["duration"].max())
    ult_min = int(ult_df["age"].min())
    ult = ult_df.sort_values("age")["qx"].to_numpy(dtype=float)
    return SelectUltimateTable(
        name=f"2015 VBT {sex.title()} {smoker_status} RR100",
        _select=select,
        _ult=ult,
        ult_min_age=ult_min,
        select_period=select_period,
    )


@lru_cache(maxsize=None)
def load_elt(sex: str) -> AggregateTable:
    """Load an ELT No. 15 (1990-92) population life table."""
    df = pd.read_csv(_DATA / "elt" / f"{_ELT_LABELS[sex]}.csv").sort_values("age")
    return AggregateTable(
        name=f"ELT No. 15 (1990-92) {sex.title()}",
        _qx=df["qx"].to_numpy(dtype=float),
        min_age=int(df["age"].min()),
    )


class ConstantMortalityTable(MortalityTable):
    """Flat mortality rate at every age - used to validate the engine against
    closed-form results in the tests."""

    def __init__(self, q: float):
        self.name = f"Constant q={q}"
        self._q = float(q)

    def q(self, issue_age: int, policy_year: int) -> float:  # noqa: ARG002
        return self._q
