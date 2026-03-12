"""Tests for io module."""
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from scoreSEND.io import get_study_ids_from_xpt, read_domain_for_study


def test_get_study_ids_from_xpt_empty(tmp_path):
    """Empty or missing dir returns empty DataFrame."""
    out = get_study_ids_from_xpt(str(tmp_path))
    assert isinstance(out, pd.DataFrame)
    assert "study_dir" in out.columns
    assert len(out) == 0


def test_get_study_ids_from_xpt_subdirs(tmp_path):
    """Subdirs are returned as study_dir."""
    (tmp_path / "study1").mkdir()
    (tmp_path / "study2").mkdir()
    out = get_study_ids_from_xpt(str(tmp_path))
    assert len(out) == 2
    assert set(out["study_dir"].str.replace("\\", "/").str.split("/").str[-1]) == {"study1", "study2"}


def test_read_domain_requires_path_or_xpt():
    """Either path_db or xpt_dir must be provided."""
    with pytest.raises(ValueError, match="path_db or xpt_dir"):
        read_domain_for_study("dm", studyid="x", path_db=None, xpt_dir=None)


def test_read_domain_requires_studyid_for_sqlite():
    """studyid required when using path_db."""
    with pytest.raises(ValueError, match="studyid"):
        read_domain_for_study("dm", studyid=None, path_db="/fake/path.db", xpt_dir=None)
