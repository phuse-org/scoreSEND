"""
Body weight (BW) scoring: z-score using vehicle mean/SD, all subjects.
"""

from typing import Optional

import numpy as np
import pandas as pd

from ..io import read_domain_for_study
from ..compile_data import get_compile_data


def get_bw_score(
    studyid: Optional[str] = None,
    path_db: Optional[str] = None,
    fake_study: bool = False,
    master_CompileData: Optional[pd.DataFrame] = None,
    score_in_list_format: bool = False,
    xpt_dir: Optional[str] = None,
) -> pd.DataFrame:
    """
    BW score: z-score of final body weight (change from initial) using vehicle mean/SD.
    Scores for all subjects (all treatment arms).

    Parameters
    ----------
    studyid, path_db, xpt_dir : optional
        Data source (SQLite or XPT directory).
    fake_study : bool
        Whether study is SENDsanitizer-style (DM+TS only).
    master_CompileData : DataFrame or None
        Precomputed compile data; if None, get_compile_data is called.
    score_in_list_format : bool
        If False, return long format (STUDYID, USUBJID, endpoint, score, SEX).
        If True, return wide (bwzscore_BW-style with BWZSCORE, finalbodyweight, etc.).

    Returns
    -------
    pandas.DataFrame
    """
    use_xpt = xpt_dir is not None
    if not use_xpt:
        if path_db is None or studyid is None:
            raise ValueError("path_db and studyid are required when xpt_dir is not set.")
        studyid = str(studyid)

    if use_xpt:
        bw = read_domain_for_study("bw", None, path_db, xpt_dir)
    else:
        import sqlite3
        with sqlite3.connect(path_db) as con:
            bw = pd.read_sql_query(
                'SELECT * FROM BW WHERE STUDYID = ?', con, params=(studyid,)
            )
    if bw.empty:
        return _empty_bw_long() if not score_in_list_format else _empty_bw_wide()

    # Coalesce VISITDY
    for col in ["VISITDY", "BWNOMDY", "BWDY"]:
        if col not in bw.columns:
            bw[col] = np.nan
    bw["VISITDY"] = bw["VISITDY"].fillna(bw["BWNOMDY"]).fillna(bw["BWDY"])
    if bw["VISITDY"].isna().all():
        raise ValueError("BW domain must have at least one of VISITDY, BWNOMDY, or BWDY.")

    if master_CompileData is None:
        master_CompileData = get_compile_data(
            studyid=studyid, path_db=path_db, fake_study=fake_study, xpt_dir=xpt_dir
        )
    if master_CompileData.empty:
        return _empty_bw_long() if not score_in_list_format else _empty_bw_wide()

    # Initial weight per subject
    base_cols = [c for c in ["STUDYID", "USUBJID", "BWSTRESN", "VISITDY", "BWBLFL"] if c in bw.columns]
    initial_rows = []
    for usubjid, grp in bw.groupby("USUBJID"):
        grp = grp.sort_values("VISITDY")
        row = None
        # 1. VISITDY == 1
        one = grp[grp["VISITDY"] == 1]
        if len(one) > 0:
            row = one.iloc[0][base_cols]
        # 2. VISITDY < 0 closest to 0
        if row is None:
            neg = grp[grp["VISITDY"] < 0]
            if len(neg) > 0:
                idx = (neg["VISITDY"]).abs().idxmin()
                row = neg.loc[idx, base_cols]
        # 3. 1 < VISITDY <= 5 min
        if row is None:
            mid = grp[(grp["VISITDY"] > 1) & (grp["VISITDY"] <= 5)]
            if len(mid) > 0:
                idx = mid["VISITDY"].idxmin()
                row = mid.loc[idx, base_cols]
        # 4. VISITDY > 5, use 0 for BWSTRESN
        if row is None:
            big = grp[grp["VISITDY"] > 5]
            if len(big) > 0:
                idx = big["VISITDY"].idxmin()
                row = big.loc[idx, base_cols].copy()
                row["BWSTRESN"] = 0
        if row is not None:
            initial_rows.append(row)
    if not initial_rows:
        return _empty_bw_long() if not score_in_list_format else _empty_bw_wide()
    study_initial = pd.DataFrame(initial_rows).drop_duplicates(subset=["USUBJID"], keep="first")

    # Final weight: TERMBW or max VISITDY > 5
    body_cols = [c for c in ["STUDYID", "USUBJID", "BWTESTCD", "BWSTRESN", "VISITDY", "BWBLFL"] if c in bw.columns]
    final_rows = []
    for usubjid, grp in bw.groupby("USUBJID"):
        termbw = grp[grp["BWTESTCD"] == "TERMBW"] if "BWTESTCD" in grp.columns else pd.DataFrame()
        if len(termbw) > 0:
            final_rows.append(termbw.iloc[0][body_cols])
        else:
            pos = grp[grp["VISITDY"] > 5]
            if len(pos) > 0:
                idx = pos["VISITDY"].idxmax()
                final_rows.append(pos.loc[idx, body_cols])
    if not final_rows:
        return _empty_bw_long() if not score_in_list_format else _empty_bw_wide()
    study_body = pd.DataFrame(final_rows).drop_duplicates(subset=["USUBJID"], keep="first")

    # Restrict to compile data subjects
    valid_usubjids = set(master_CompileData["USUBJID"])
    study_initial = study_initial[study_initial["USUBJID"].isin(valid_usubjids)]
    study_body = study_body[study_body["USUBJID"].isin(valid_usubjids)]
    if study_initial.empty or study_body.empty:
        return _empty_bw_long() if not score_in_list_format else _empty_bw_wide()

    # Join initial and final (need BWSTRESN_Init from initial)
    if "BWSTRESN" in study_initial.columns:
        study_initial = study_initial.rename(columns={"BWSTRESN": "BWSTRESN_Init"})
    merged = study_body.merge(
        study_initial[["USUBJID", "BWSTRESN_Init"]],
        on="USUBJID",
        how="inner",
    )
    compile_sub = master_CompileData[["USUBJID", "ARMCD", "SETCD", "SEX"]].drop_duplicates()
    merged = merged.merge(compile_sub, on="USUBJID", how="inner")
    if "STUDYID" not in merged.columns and "STUDYID" in study_body.columns:
        merged["STUDYID"] = study_body["STUDYID"].iloc[0]
    merged["finalbodyweight"] = (merged["BWSTRESN"] - merged["BWSTRESN_Init"]).abs()
    merged = merged.reset_index(drop=True)

    # Z-score by study: vehicle mean/sd
    def zscore(g):
        armcd = g["ARMCD"]
        if isinstance(armcd, pd.DataFrame):
            armcd = armcd.iloc[:, 0]
        mask = (armcd == "vehicle").values
        v = g.loc[mask]
        m = v["finalbodyweight"].mean(skipna=True)
        s = v["finalbodyweight"].std(skipna=True)
        if pd.isna(s) or s == 0:
            return g.assign(BWZSCORE=np.nan)
        return g.assign(BWZSCORE=(g["finalbodyweight"] - m) / s)

    merged = merged.groupby("STUDYID", group_keys=False).apply(zscore)
    merged = merged.reset_index(drop=True)

    if score_in_list_format:
        return merged
    long_df = merged[["STUDYID", "USUBJID", "SEX"]].copy()
    long_df["endpoint"] = "BW"
    long_df["score"] = merged["BWZSCORE"]
    return long_df


def _empty_bw_long() -> pd.DataFrame:
    return pd.DataFrame(columns=["STUDYID", "USUBJID", "endpoint", "score", "SEX"])


def _empty_bw_wide() -> pd.DataFrame:
    return pd.DataFrame(columns=["STUDYID", "USUBJID", "ARMCD", "SETCD", "SEX", "BWSTRESN", "BWSTRESN_Init", "finalbodyweight", "BWZSCORE"])
