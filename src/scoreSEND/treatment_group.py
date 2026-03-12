"""
Get treatment group, recovery group, and TK group per study from TX, TS, DS, DM, PC, pooldef.
"""

import sqlite3
from pathlib import Path
from typing import Optional, List

import pandas as pd

from .io import read_domain_for_study


def get_treatment_group(
    studies: Optional[List[str]] = None,
    db_path: Optional[str] = None,
    xpt_dir: Optional[str] = None,
) -> dict:
    """
    For each study, return species, setcd list, treatment_group (SETCDs with TERMINAL SACRIFICE),
    recovery_group (SETCDs with RECOVERY SACRIFICE), and TK_group (for rat studies).

    Parameters
    ----------
    studies : list of str or None
        Study IDs for SQLite; if None, use ID table. Ignored when xpt_dir is set.
    db_path : str or None
        Path to SQLite database; required when xpt_dir is not set.
    xpt_dir : str or None
        Path to directory containing XPT files for one study.

    Returns
    -------
    dict
        Keys: study ID (or single study when xpt_dir), each value is dict with species, setcd,
        treatment_group, recovery_group, TK_group (if rat). Plus key 'four_trtm_group' with list of studies that have 4 treatment groups.
    """
    list_return = {}
    four = []

    use_xpt = xpt_dir is not None
    if use_xpt:
        study_list = pd.DataFrame({"study_dir": [str(xpt_dir)]})
    else:
        if db_path is None:
            raise ValueError("db_path is required when xpt_dir is not set.")
        import sqlite3
        with sqlite3.connect(db_path) as con:
            if studies is None:
                id_df = pd.read_sql_query("SELECT * FROM ID", con)
                studies = id_df["STUDYID"].tolist()
                study_list = id_df[["APPID", "STUDYID"]].copy()
                study_list.columns = ["APPID", "STUDYID"]
            else:
                study_list = pd.DataFrame({"APPID": [None] * len(studies), "STUDYID": studies})

    for i in range(len(study_list)):
        if use_xpt:
            study_dir_val = study_list.loc[i, "study_dir"]
            study = Path(study_dir_val).name
            tx = read_domain_for_study("tx", None, None, study_dir_val)
            ts = read_domain_for_study("ts", None, None, study_dir_val)
            ds = read_domain_for_study("ds", None, None, study_dir_val)
            dm = read_domain_for_study("dm", None, None, study_dir_val)
            pc = read_domain_for_study("pc", None, None, study_dir_val)
            pooldef = read_domain_for_study("pooldef", None, None, study_dir_val)
        else:
            study = study_list.loc[i, "STUDYID"]
            with sqlite3.connect(db_path) as con:
                tx = pd.read_sql_query("SELECT STUDYID, SETCD, TXPARMCD, TXVAL FROM TX WHERE STUDYID = ?", con, params=(study,))
                ts = pd.read_sql_query("SELECT STUDYID, TSPARMCD, TSVAL FROM TS WHERE STUDYID = ?", con, params=(study,))
                ds = pd.read_sql_query("SELECT STUDYID, USUBJID, DSDECOD FROM DS WHERE STUDYID = ?", con, params=(study,))
                dm = pd.read_sql_query("SELECT STUDYID, USUBJID, SETCD FROM DM WHERE STUDYID = ?", con, params=(study,))
                pc = pd.read_sql_query("SELECT STUDYID, USUBJID, POOLID FROM PC WHERE STUDYID = ?", con, params=(study,))
                pooldef = pd.read_sql_query("SELECT STUDYID, USUBJID, POOLID FROM POOLDEF WHERE STUDYID = ?", con, params=(study,))

        number_of_setcd = dm["SETCD"].dropna().unique().tolist() if not dm.empty else []
        st_species = ts.loc[ts["TSPARMCD"] == "SPECIES", "TSVAL"].tolist() if not ts.empty else []
        st_species = st_species[0] if st_species else None
        list_return[study] = {"species": st_species, "setcd": number_of_setcd}
        recv_group = []
        trtm_group = []

        if st_species is None:
            list_return[study]["treatment_group"] = trtm_group
            list_return[study]["recovery_group"] = recv_group
            list_return[study]["TK_group"] = []
            continue

        species_lower = str(st_species).lower()
        tk_group = []
        not_tk = number_of_setcd

        if "rat" in species_lower:
            parmcd = tx["TXPARMCD"].dropna().unique().tolist() if not tx.empty else []
            tkdesc_in_parmcd = "TKDESC" in parmcd
            if tkdesc_in_parmcd and not tx.empty:
                tkdesc_vals = tx.loc[tx["TXPARMCD"] == "TKDESC", "TXVAL"].dropna().unique().tolist()
                if tkdesc_vals and "TK" in tkdesc_vals:
                    tk_group = tx.loc[(tx["TXPARMCD"] == "TKDESC") & (tx["TXVAL"] == "TK"), "SETCD"].dropna().unique().tolist()
                not_tk = [s for s in number_of_setcd if s not in tk_group]
            else:
                uniq_pool = pc["POOLID"].dropna().unique().tolist() if not pc.empty else []
                pool_sub = set()
                if pooldef.empty or uniq_pool is None:
                    pass
                else:
                    pool_sub = set(pooldef.loc[pooldef["POOLID"].isin(uniq_pool), "USUBJID"])
                pc_subj = pc["USUBJID"].dropna().unique().tolist() if not pc.empty else []
                for set_cd in number_of_setcd:
                    subjid = dm.loc[dm["SETCD"] == set_cd, "USUBJID"].dropna().unique().tolist()
                    if pc_subj and any(s in pc_subj for s in subjid):
                        tk_group.append(set_cd)
                    elif pool_sub and any(s in pool_sub for s in subjid):
                        tk_group.append(set_cd)
                not_tk = [s for s in number_of_setcd if s not in tk_group]
            list_return[study]["TK_group"] = tk_group

        for set_cd in not_tk:
            subjid = dm.loc[dm["SETCD"] == set_cd, "USUBJID"].dropna().unique().tolist()
            if not subjid or ds.empty:
                continue
            dsdecod = ds.loc[ds["USUBJID"].isin(subjid), "DSDECOD"].dropna().str.lower().unique().tolist()
            if "recovery sacrifice" in dsdecod:
                recv_group.append(set_cd)
            elif "terminal sacrifice" in dsdecod:
                trtm_group.append(set_cd)

        list_return[study]["treatment_group"] = trtm_group
        list_return[study]["recovery_group"] = recv_group
        if "TK_group" not in list_return[study]:
            list_return[study]["TK_group"] = []
        if len(trtm_group) == 4:
            four.append(study)

    list_return["four_trtm_group"] = four
    return list_return
