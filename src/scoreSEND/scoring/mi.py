"""
Microscopic findings (MI) liver scoring: severity normalization, per-subject highest_score, study mean.
"""

import re
from typing import Optional

import numpy as np
import pandas as pd

from ..io import read_domain_for_study
from ..compile_data import get_compile_data


def _normalize_misev(ser: pd.Series) -> pd.Series:
    s = ser.astype(str).str.strip().replace("", "0")
    s = s.replace(np.nan, "0")
    s = s.str.upper()
    repl = [
        (r"\b1\s*OF\s*4\b", "2"),
        (r"\b2\s*OF\s*4\b", "3"),
        (r"\b3\s*OF\s*4\b", "4"),
        (r"\b4\s*OF\s*4\b", "5"),
        ("1 OF 5", "1"),
        ("MINIMAL", "1"),
        ("2 OF 5", "2"),
        ("MILD", "2"),
        ("3 OF 5", "3"),
        ("MODERATE", "3"),
        ("4 OF 5", "4"),
        ("MARKED", "4"),
        ("5 OF 5", "5"),
        ("SEVERE", "5"),
    ]
    for pat, val in repl:
        s = s.str.replace(pat, val, regex=True)
    return s.fillna("0").replace("", "0")


def get_mi_score(
    studyid: Optional[str] = None,
    path_db: Optional[str] = None,
    fake_study: bool = False,
    master_CompileData: Optional[pd.DataFrame] = None,
    score_in_list_format: bool = False,
    xpt_dir: Optional[str] = None,
) -> pd.DataFrame:
    """
    MI liver score: severity-normalized findings, per-subject highest_score, study-level mean over all subjects.
    """
    use_xpt = xpt_dir is not None
    if not use_xpt and (path_db is None or studyid is None):
        raise ValueError("path_db and studyid are required when xpt_dir is not set.")
    studyid = str(studyid) if studyid else None

    if use_xpt:
        mi = read_domain_for_study("mi", None, path_db, xpt_dir)
    else:
        import sqlite3
        with sqlite3.connect(path_db) as con:
            mi = pd.read_sql_query("SELECT * FROM MI WHERE STUDYID = ?", con, params=(studyid,))
    if mi.empty:
        return _empty_mi_long() if not score_in_list_format else _empty_mi_wide()

    midata = mi[mi["MISPEC"].astype(str).str.upper().str.contains("LIVER", na=False)][
        ["USUBJID", "MISTRESC", "MISEV", "MISPEC"]
    ].copy()
    if midata.empty:
        return _empty_mi_long() if not score_in_list_format else _empty_mi_wide()

    midata["MISEV"] = _normalize_misev(midata["MISEV"])
    midata = midata.dropna(subset=["MISTRESC"])
    midata["MISTRESC"] = midata["MISTRESC"].astype(str).str.upper()
    midata = midata[midata["MISTRESC"] != ""]

    # Merge finding levels
    midata["MISTRESC"] = midata["MISTRESC"].replace({
        "CELL DEBRIS": "CELLULAR DEBRIS",
        "Infiltration, mixed cell": "Infiltrate",
        "Infiltration, mononuclear cell": "Infiltrate",
        "INFILTRATION, MONONUCLEAR CELL": "Infiltrate",
        "Fibrosis": "Fibroplasia/Fibrosis",
    })

    if master_CompileData is None:
        master_CompileData = get_compile_data(
            studyid=studyid, path_db=path_db, fake_study=fake_study, xpt_dir=xpt_dir
        )
    if master_CompileData.empty:
        return _empty_mi_long() if not score_in_list_format else _empty_mi_wide()

    midata = midata[midata["USUBJID"].isin(master_CompileData["USUBJID"])]
    if midata.empty:
        return _empty_mi_long() if not score_in_list_format else _empty_mi_wide()

    pivot = midata.pivot_table(
        index="USUBJID", columns="MISTRESC", values="MISEV", aggfunc="first"
    ).fillna("0")
    for c in pivot.columns:
        pivot[c] = pd.to_numeric(pivot[c], errors="coerce").fillna(0)
    if "NORMAL" in pivot.columns:
        pivot = pivot.drop(columns=["NORMAL"], errors="ignore")
    if pivot.empty:
        return _empty_mi_long() if not score_in_list_format else _empty_mi_wide()

    compile_sub = master_CompileData[["STUDYID", "USUBJID", "ARMCD", "SETCD", "SEX"]].drop_duplicates()
    mi_compile = compile_sub.merge(pivot.reset_index(), on="USUBJID", how="inner")
    finding_cols = [c for c in mi_compile.columns if c not in ["STUDYID", "USUBJID", "ARMCD", "SETCD", "SEX"]]
    if not finding_cols:
        return _empty_mi_long() if not score_in_list_format else _empty_mi_wide()

    # Severity transform: 5->5, >3->3, 3->2, >0->1, 0->0
    scored = mi_compile.copy()
    for col in finding_cols:
        x = pd.to_numeric(scored[col], errors="coerce").fillna(0)
        scored[col] = np.where(x == 5, 5,
            np.where(x > 3, 3,
                np.where(x == 3, 2,
                    np.where(x > 0, 1, 0))))
    scored["highest_score"] = scored[finding_cols].max(axis=1)

    if score_in_list_format:
        return scored

    long_df = scored.melt(
        id_vars=["STUDYID", "USUBJID"],
        value_vars=finding_cols,
        var_name="endpoint",
        value_name="score",
    )[["STUDYID", "USUBJID", "endpoint", "score"]]
    return long_df


def _empty_mi_long() -> pd.DataFrame:
    return pd.DataFrame(columns=["STUDYID", "USUBJID", "endpoint", "score"])


def _empty_mi_wide() -> pd.DataFrame:
    return pd.DataFrame(columns=["STUDYID", "USUBJID", "ARMCD", "SETCD", "SEX"])
