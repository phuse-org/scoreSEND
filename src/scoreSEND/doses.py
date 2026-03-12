"""
Return dose/arm table for a study (same subject-level compile data as get_compile_data, main path).
"""

from typing import Optional

import pandas as pd

from .compile_data import get_compile_data


def get_doses(
    studyid: Optional[str] = None,
    path_db: Optional[str] = None,
    xpt_dir: Optional[str] = None,
) -> pd.DataFrame:
    """
    Return dose/arm table for the study: one row per subject with ARMCD (vehicle, HD, Intermediate, Both).
    Uses the same recovery/TK cleaning and dose-ranking logic as get_compile_data (main path, fake_study=False).

    Parameters
    ----------
    studyid : str or None
        Required for SQLite; optional when xpt_dir is set.
    path_db : str or None
        Path to SQLite database; required when xpt_dir is not set.
    xpt_dir : str or None
        Path to directory containing XPT files for one study.

    Returns
    -------
    pandas.DataFrame
        Columns: STUDYID, USUBJID, Species, SEX, ARMCD, SETCD.
    """
    return get_compile_data(
        studyid=studyid,
        path_db=path_db,
        fake_study=False,
        xpt_dir=xpt_dir,
    )
