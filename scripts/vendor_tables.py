"""Fetch real public actuarial tables from the SOA table library (mort.soa.org)
via pymort and vendor them into the basis package as CSV. Run once, offline thereafter.

Sources (all public):
  2015 VBT Smoker-Distinct, RR100, Select & Ultimate  -> life term assurance
  ELT No. 15 (1990-92) population life tables          -> funeral whole-of-life
"""
from pathlib import Path
import pandas as pd
from pymort import MortXML

OUT = Path(__file__).resolve().parents[1] / "src" / "basis" / "data"

VBT = {  # label -> SOA table id
    "male_ns": 3252, "male_sm": 3258,
    "female_ns": 3224, "female_sm": 3230,
}
ELT = {"male": 1705, "female": 1704}

def vendor_vbt():
    for label, tid in VBT.items():
        x = MortXML.from_id(tid)
        sel = x.Tables[0].Values.reset_index()
        sel.columns = ["issue_age", "duration", "qx"]
        sel.to_csv(OUT / "vbt" / f"{label}.select.csv", index=False)
        ult = x.Tables[1].Values.reset_index()
        ult.columns = ["age", "qx"]
        ult.to_csv(OUT / "vbt" / f"{label}.ult.csv", index=False)
        name = x.ContentClassification.TableName
        print(f"VBT {label:9} id={tid} '{name}' select={len(sel)} ult={len(ult)}")

def vendor_elt():
    for label, tid in ELT.items():
        x = MortXML.from_id(tid)
        v = x.Tables[0].Values.reset_index()
        v.columns = ["age", "qx"]
        v.to_csv(OUT / "elt" / f"{label}.csv", index=False)
        print(f"ELT {label:9} id={tid} '{x.ContentClassification.TableName}' n={len(v)}")

if __name__ == "__main__":
    vendor_vbt(); vendor_elt()
    print("Done ->", OUT)
