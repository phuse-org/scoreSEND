"""
Get scores for multiple domains (bw, lb, mi) in one call.
"""

from typing import Optional, List

from .compile_data import get_compile_data
from .scoring.bw import get_bw_score
from .scoring.lb import get_lb_score
from .scoring.mi import get_mi_score


def get_all_score(
    studyid: Optional[str] = None,
    path_db: Optional[str] = None,
    domain: Optional[List[str]] = None,
    fake_study: bool = False,
    xpt_dir: Optional[str] = None,
) -> dict:
    """
    Get scores for requested domains (bw, lb, mi). Returns a dict with studyid_res and one key per domain.

    Parameters
    ----------
    studyid, path_db, xpt_dir : optional
        Data source.
    domain : list of str
        One or more of "lb", "mi", "bw". Default: ["lb", "mi", "bw"].
    fake_study : bool
        Whether study is SENDsanitizer-style.

    Returns
    -------
    dict
        Keys: studyid_res, and each entry in domain (e.g. "bw", "lb", "mi") with the score DataFrame.
    """
    if domain is None:
        domain = ["lb", "mi", "bw"]
    use_xpt = xpt_dir is not None
    if not use_xpt and studyid is None:
        raise ValueError("studyid is required when xpt_dir is not set (SQLite).")
    studyid_res = str(studyid) if studyid else (xpt_dir if use_xpt else None)
    if studyid_res and hasattr(studyid_res, "split"):
        import os
        studyid_res = os.path.basename(str(studyid_res))
    result = {"studyid_res": studyid_res}
    for d in domain:
        if d == "lb":
            result["lb"] = get_lb_score(studyid=studyid, path_db=path_db, fake_study=fake_study, xpt_dir=xpt_dir)
        elif d == "mi":
            result["mi"] = get_mi_score(studyid=studyid, path_db=path_db, fake_study=fake_study, xpt_dir=xpt_dir)
        elif d == "bw":
            result["bw"] = get_bw_score(studyid=studyid, path_db=path_db, fake_study=fake_study, xpt_dir=xpt_dir)
        else:
            raise ValueError("check your domain")
    return result
