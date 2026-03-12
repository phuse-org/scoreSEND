"""
Build compile data: subject-level table with ARMCD (vehicle, HD, Intermediate, Both),
excluding recovery and TK animals.
"""

import re
from typing import Optional

import pandas as pd

from .io import read_domain_for_study


def get_compile_data(
    studyid: Optional[str] = None,
    path_db: Optional[str] = None,
    fake_study: bool = False,
    xpt_dir: Optional[str] = None,
) -> pd.DataFrame:
    """
    Build compile data: one row per subject, excluding recovery and (when applicable) TK animals.
    Assigns ARMCD (vehicle, HD, Intermediate, or Both) for scoring.

    Parameters
    ----------
    studyid : str or None
        Required for SQLite; optional when xpt_dir is set.
    path_db : str or None
        Path to SQLite database; required when xpt_dir is not set.
    fake_study : bool
        If True, use DM + TS only and keep all arms from DM (SENDsanitizer-style).
    xpt_dir : str or None
        Path to directory containing XPT files for one study.

    Returns
    -------
    pandas.DataFrame
        Columns: STUDYID, USUBJID, Species, SEX, ARMCD, SETCD.
    """
    use_xpt = xpt_dir is not None
    if not use_xpt:
        if path_db is None:
            raise ValueError("path_db is required when xpt_dir is not set.")
        if studyid is None:
            raise ValueError("studyid is required when xpt_dir is not set (SQLite).")
        studyid = str(studyid)

    if fake_study:
        if use_xpt:
            dm = read_domain_for_study("dm", studyid=None, path_db=path_db, xpt_dir=xpt_dir)
            ts = read_domain_for_study("ts", studyid=None, path_db=path_db, xpt_dir=xpt_dir)
        else:
            dm = _con_db(studyid, path_db, "dm")
            ts = _con_db(studyid, path_db, "ts")
        if dm.empty or ts.empty:
            return _empty_compile()
        species = ts.loc[ts["TSPARMCD"] == "SPECIES", "TSVAL"].iloc[0]
        cols = [c for c in ["STUDYID", "USUBJID", "SPECIES", "SEX", "ARMCD", "ARM", "SETCD"] if c in dm.columns]
        dm = dm[cols].copy()
        if "ARM" in dm.columns and "ARMCD" in dm.columns:
            dm["ARMCD"] = dm["ARM"]
            dm = dm.drop(columns=["ARM"], errors="ignore")
        elif "ARM" in dm.columns:
            dm["ARMCD"] = dm["ARM"]
            dm = dm.drop(columns=["ARM"], errors="ignore")
        if "SPECIES" in dm.columns:
            dm = dm.drop(columns=["SPECIES"], errors="ignore")
        dm["Species"] = species
        dm.loc[dm["ARMCD"] == "Control", "ARMCD"] = "vehicle"
        return dm

    if use_xpt:
        bw = read_domain_for_study("bw", None, path_db, xpt_dir)
        dm = read_domain_for_study("dm", None, path_db, xpt_dir)
        ds = read_domain_for_study("ds", None, path_db, xpt_dir)
        ts = read_domain_for_study("ts", None, path_db, xpt_dir)
        tx = read_domain_for_study("tx", None, path_db, xpt_dir)
        pooldef = read_domain_for_study("pooldef", None, path_db, xpt_dir)
        pp = read_domain_for_study("pp", None, path_db, xpt_dir)
    else:
        dm = _con_db(studyid, path_db, "dm")
        ds = _con_db(studyid, path_db, "ds")
        ts = _con_db(studyid, path_db, "ts")
        tx = _con_db(studyid, path_db, "tx")
        pooldef = _con_db(studyid, path_db, "pooldef")
        pp = _con_db(studyid, path_db, "pp")

    if ts.empty or dm.empty:
        return _empty_compile()

    species = ts.loc[ts["TSPARMCD"] == "SPECIES", "TSVAL"].iloc[0]
    studyid_val = ts["STUDYID"].iloc[0]

    compile_data = pd.DataFrame({
        "STUDYID": [studyid_val] * len(dm),
        "Species": [species] * len(dm),
        "USUBJID": dm["USUBJID"].values,
        "SEX": dm["SEX"].values,
        "ARMCD": dm["ARMCD"].values,
        "SETCD": dm["SETCD"].values,
    })
    compile_data = compile_data.dropna(how="all")

    # Remove recovery: keep only DSDECOD in allowed set
    if not ds.empty and "DSDECOD" in ds.columns:
        allowed = [
            "TERMINAL SACRIFICE",
            "MORIBUND SACRIFICE",
            "REMOVED FROM STUDY ALIVE",
            "NON-MORIBUND SACRIFICE",
        ]
        filtered_ds = ds[ds["DSDECOD"].isin(allowed)]
        valid_usubjids = set(filtered_ds["USUBJID"].dropna())
        compile_data = compile_data[compile_data["USUBJID"].isin(valid_usubjids)]
    if compile_data.empty:
        return _empty_compile()

    # Remove TK (rat only)
    species_lower = str(species).lower()
    if "rat" in species_lower and not pp.empty and not pooldef.empty and "POOLID" in pp.columns:
        tk_pools = set(pp["POOLID"].dropna())
        if tk_pools and "USUBJID" in pooldef.columns:
            tk_usubjids = set(pooldef.loc[pooldef["POOLID"].isin(tk_pools), "USUBJID"])
            compile_data = compile_data[~compile_data["USUBJID"].isin(tk_usubjids)]
    if compile_data.empty:
        return _empty_compile()

    # Dose ranking from TX TRTDOS
    tx_trt = tx[tx["TXPARMCD"] == "TRTDOS"].copy() if not tx.empty and "TXPARMCD" in tx.columns else pd.DataFrame()
    if tx_trt.empty:
        return compile_data.rename(columns={})  # no ARMCD from dose

    clean_pattern = re.compile(r"[;|\-/:,]")
    rows = []
    for _, row in tx_trt.iterrows():
        val = row.get("TXVAL")
        if pd.isna(val):
            rows.append({**row.to_dict(), "TXVAL": float("nan")})
            continue
        s = str(val).strip()
        parts = clean_pattern.split(s)
        for p in parts:
            p = p.strip()
            if not p:
                continue
            try:
                n = float(p)
            except ValueError:
                n = float("nan")
            rows.append({
                "STUDYID": row["STUDYID"],
                "SETCD": row["SETCD"],
                "TXPARMCD": row["TXPARMCD"],
                "TXVAL": n,
            })
    if not rows:
        return compile_data
    clean_tx = pd.DataFrame(rows)
    dose_ranking = (
        clean_tx.groupby(["STUDYID", "SETCD"], as_index=False)["TXVAL"]
        .min()
    )
    dose_ranking.loc[dose_ranking["TXVAL"].isin([float("inf"), float("-inf")]), "TXVAL"] = float("nan")
    study_min = dose_ranking.groupby("STUDYID")["TXVAL"].transform("min")
    study_max = dose_ranking.groupby("STUDYID")["TXVAL"].transform("max")
    dose_ranking["DOSE_RANKING"] = "Intermediate"
    dose_ranking.loc[dose_ranking["TXVAL"] == study_min, "DOSE_RANKING"] = "vehicle"
    dose_ranking.loc[dose_ranking["TXVAL"] == study_max, "DOSE_RANKING"] = "HD"
    dose_ranking.loc[study_min == study_max, "DOSE_RANKING"] = "Both"
    dose_ranked = dose_ranking[["STUDYID", "SETCD", "DOSE_RANKING"]]

    merged = compile_data.merge(dose_ranked, on=["STUDYID", "SETCD"], how="inner")
    merged = merged.rename(columns={"DOSE_RANKING": "ARMCD"})
    return merged[["STUDYID", "USUBJID", "Species", "SEX", "ARMCD", "SETCD"]]


def _con_db(studyid: str, path_db: str, domain: str) -> pd.DataFrame:
    import sqlite3
    dom = domain.upper()
    with sqlite3.connect(path_db) as con:
        return pd.read_sql_query(f'SELECT * FROM "{dom}" WHERE STUDYID = ?', con, params=(studyid,))


def _empty_compile() -> pd.DataFrame:
    return pd.DataFrame(columns=["STUDYID", "USUBJID", "Species", "SEX", "ARMCD", "SETCD"])
