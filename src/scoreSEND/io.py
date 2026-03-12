"""
Internal helpers for reading SEND domains from SQLite or flat XPT directories.
read_domain_for_study is used by get_doses, get_compile_data, scoring, etc.
get_study_ids_from_xpt is exported to list study directories under a parent.
"""

import sqlite3
from pathlib import Path
from typing import Optional

import pandas as pd
import pyreadstat


def read_domain_for_study(
    domain: str,
    studyid: Optional[str] = None,
    path_db: Optional[str] = None,
    xpt_dir: Optional[str] = None,
) -> pd.DataFrame:
    """
    Read a single domain from SQLite or from a directory of XPT files (flat layout).

    When xpt_dir is set, it is the path to a directory that directly contains
    domain files (e.g. bw.xpt, dm.xpt). studyid is not used for path construction.
    When path_db is set, studyid is required for the SQLite query.

    Parameters
    ----------
    domain : str
        Lowercase domain name (e.g. "dm", "bw", "lb").
    studyid : str or None
        Required for SQLite (WHERE STUDYID = ?); ignored when xpt_dir is set.
    path_db : str or None
        Path to SQLite database (used when xpt_dir is None).
    xpt_dir : str or None
        Path to a directory containing XPT files for one study (flat: xpt_dir/domain.xpt).

    Returns
    -------
    pandas.DataFrame
        Domain data with uppercase column names.
    """
    domain = domain.lower()
    if xpt_dir is not None:
        xpt_path = Path(xpt_dir) / f"{domain}.xpt"
        if not xpt_path.exists():
            return pd.DataFrame()
        df, _ = pyreadstat.read_xport(str(xpt_path))
        if df is None or len(df) == 0:
            return pd.DataFrame()
        df.columns = [c.upper() for c in df.columns]
        return df
    if path_db is None:
        raise ValueError("Either path_db or xpt_dir must be provided.")
    if studyid is None:
        raise ValueError("studyid is required when using path_db (SQLite).")
    studyid = str(studyid)
    dom = domain.upper()
    with sqlite3.connect(path_db) as con:
        q = f'SELECT * FROM "{dom}" WHERE STUDYID = ?'
        out = pd.read_sql_query(q, con, params=(studyid,))
    return out


def get_study_ids_from_xpt(parent_dir: str) -> pd.DataFrame:
    """
    List study directories under a parent path (flat XPT layout).

    Returns immediate subdirectories of parent_dir; each subdir is assumed to be
    a study folder containing XPT files (e.g. bw.xpt, dm.xpt). Use to iterate
    over multiple studies when parent_dir contains one subdir per study.

    Parameters
    ----------
    parent_dir : str
        Path to a parent directory whose subdirs are study folders.

    Returns
    -------
    pandas.DataFrame
        One column: study_dir (full path to each study directory).
    """
    p = Path(parent_dir)
    if not p.is_dir():
        return pd.DataFrame({"study_dir": []})
    subdirs = [str(d) for d in p.iterdir() if d.is_dir()]
    return pd.DataFrame({"study_dir": subdirs})
