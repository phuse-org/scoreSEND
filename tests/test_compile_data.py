"""Tests for compile_data module."""
import pandas as pd
import pytest

from scoreSEND.compile_data import get_compile_data


def test_get_compile_data_requires_path_or_xpt():
    with pytest.raises(ValueError, match="path_db"):
        get_compile_data(studyid="x", path_db=None, xpt_dir=None)


def test_get_compile_data_requires_studyid_when_no_xpt():
    with pytest.raises(ValueError, match="studyid"):
        get_compile_data(studyid=None, path_db="/fake/db.db", xpt_dir=None)


def test_empty_compile_columns():
    """Empty compile has expected columns."""
    from scoreSEND.compile_data import _empty_compile
    out = _empty_compile()
    assert list(out.columns) == ["STUDYID", "USUBJID", "Species", "SEX", "ARMCD", "SETCD"]
    assert len(out) == 0
