"""
Laboratory (LB) liver scoring: z-scores per test (ALT, AST, ALP, GGT, BILI, ALB), vehicle reference.
"""

from typing import Optional

import numpy as np
import pandas as pd

from ..io import read_domain_for_study
from ..compile_data import get_compile_data

LIVER_TESTS = [
    "SERUM | ALT", "PLASMA | ALT", "WHOLE BLOOD | ALT",
    "SERUM | AST", "PLASMA | AST", "WHOLE BLOOD | AST",
    "SERUM | ALP", "PLASMA | ALP", "WHOLE BLOOD | ALP",
    "SERUM | GGT", "PLASMA | GGT", "WHOLE BLOOD | GGT",
    "SERUM | BILI", "PLASMA | BILI", "WHOLE BLOOD | BILI",
    "SERUM | ALB", "PLASMA | ALB", "WHOLE BLOOD | ALB",
]

TEST_TO_COL = {
    "alt": "alt_zscore",
    "ast": "ast_zscore",
    "alp": "alp_zscore",
    "ggt": "ggt_zscore",
    "bili": "bili_zscore",
    "alb": "alb_zscore",
}


def get_lb_score(
    studyid: Optional[str] = None,
    path_db: Optional[str] = None,
    fake_study: bool = False,
    master_CompileData: Optional[pd.DataFrame] = None,
    score_in_list_format: bool = False,
    xpt_dir: Optional[str] = None,
) -> pd.DataFrame:
    """
    LB liver score: z-scores for liver tests using vehicle mean/SD; all subjects.
    """
    use_xpt = xpt_dir is not None
    if not use_xpt and (path_db is None or studyid is None):
        raise ValueError("path_db and studyid are required when xpt_dir is not set.")
    studyid = str(studyid) if studyid else None

    if use_xpt:
        lb = read_domain_for_study("lb", None, path_db, xpt_dir)
    else:
        import sqlite3
        with sqlite3.connect(path_db) as con:
            lb = pd.read_sql_query("SELECT * FROM LB WHERE STUDYID = ?", con, params=(studyid,))
    if lb.empty:
        return _empty_lb_long() if not score_in_list_format else _empty_lb_wide()

    for col in ["VISITDY", "LBNOMDY", "LBDY"]:
        if col not in lb.columns:
            lb[col] = np.nan
    lb["VISITDY"] = lb["VISITDY"].fillna(lb["LBNOMDY"]).fillna(lb["LBDY"])
    if lb["VISITDY"].isna().all():
        raise ValueError("LB domain must have at least one of VISITDY, LBNOMDY, or LBDY.")

    if "LBSPEC" in lb.columns and "LBTESTCD" in lb.columns:
        lb = lb.copy()
        lb["LBTESTCD"] = lb["LBSPEC"].astype(str) + " | " + lb["LBTESTCD"].astype(str)
    lb = lb[lb["VISITDY"] >= 1]
    lb = lb[lb["LBTESTCD"].isin(LIVER_TESTS)]
    if lb.empty:
        return _empty_lb_long() if not score_in_list_format else _empty_lb_wide()

    max_visit = lb.groupby(["USUBJID", "LBTESTCD"], as_index=False)["VISITDY"].max()
    lb = lb.merge(max_visit, on=["USUBJID", "LBTESTCD", "VISITDY"], how="inner")

    if master_CompileData is None:
        master_CompileData = get_compile_data(
            studyid=studyid, path_db=path_db, fake_study=fake_study, xpt_dir=xpt_dir
        )
    if master_CompileData.empty:
        return _empty_lb_long() if not score_in_list_format else _empty_lb_wide()

    lb = lb.merge(
        master_CompileData[["USUBJID", "ARMCD"]].drop_duplicates(),
        on="USUBJID",
        how="inner",
    )
    if "STUDYID" not in lb.columns and len(lb):
        lb["STUDYID"] = lb["USUBJID"].str.split("-").str[0]

    def zscore_for_test(df, test_pattern, col_name):
        subset = df[df["LBTESTCD"].str.contains(test_pattern, case=False, na=False)].copy()
        if subset.empty:
            return pd.DataFrame()
        vehicle = subset[subset["ARMCD"] == "vehicle"]
        stats = vehicle.groupby("STUDYID")["LBSTRESN"].agg(["mean", "std"]).reset_index()
        stats.columns = ["STUDYID", "_mean_v", "_sd_v"]
        subset = subset.merge(stats, on="STUDYID", how="left")
        subset[col_name] = np.where(
            subset["_sd_v"].fillna(0) != 0,
            (subset["LBSTRESN"].astype(float) - subset["_mean_v"]) / subset["_sd_v"],
            np.nan,
        )
        subset[col_name] = subset[col_name].abs()
        return subset[["STUDYID", "USUBJID", "LBTESTCD", col_name]]

    z_alt = zscore_for_test(lb, "ALT", "alt_zscore")
    z_ast = zscore_for_test(lb, "AST", "ast_zscore")
    z_alp = zscore_for_test(lb, "ALP", "alp_zscore")
    z_ggt = zscore_for_test(lb, "GGT", "ggt_zscore")
    z_bili = zscore_for_test(lb, "BILI", "bili_zscore")
    z_alb = zscore_for_test(lb, "ALB", "alb_zscore")

    if score_in_list_format:
        all_usubjids = set()
        for z in [z_alt, z_ast, z_alp, z_ggt, z_bili, z_alb]:
            if not z.empty:
                all_usubjids.update(z["USUBJID"])
        wide = master_CompileData[master_CompileData["USUBJID"].isin(all_usubjids)][["STUDYID", "USUBJID", "ARMCD"]].drop_duplicates()
        for z, col in [(z_alt, "alt_zscore"), (z_ast, "ast_zscore"), (z_alp, "alp_zscore"), (z_ggt, "ggt_zscore"), (z_bili, "bili_zscore"), (z_alb, "alb_zscore")]:
            if not z.empty:
                first = z.groupby(["STUDYID", "USUBJID"]).first().reset_index()[["STUDYID", "USUBJID", col]]
                wide = wide.merge(first, on=["STUDYID", "USUBJID"], how="left")
        return wide

    long_parts = []
    for z, col in [(z_alt, "alt_zscore"), (z_ast, "ast_zscore"), (z_alp, "alp_zscore"), (z_ggt, "ggt_zscore"), (z_bili, "bili_zscore"), (z_alb, "alb_zscore")]:
        if not z.empty:
            long_parts.append(z[["STUDYID", "USUBJID", "LBTESTCD", col]].rename(columns={col: "score", "LBTESTCD": "endpoint"}))
    if not long_parts:
        return _empty_lb_long()
    return pd.concat(long_parts, ignore_index=True)[["STUDYID", "USUBJID", "endpoint", "score"]]


def _empty_lb_long() -> pd.DataFrame:
    return pd.DataFrame(columns=["STUDYID", "USUBJID", "endpoint", "score"])


def _empty_lb_wide() -> pd.DataFrame:
    return pd.DataFrame(columns=["STUDYID", "USUBJID", "ARMCD", "alt_zscore", "ast_zscore", "alp_zscore", "ggt_zscore", "bili_zscore", "alb_zscore"])
