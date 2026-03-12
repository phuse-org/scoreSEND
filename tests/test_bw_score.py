"""Tests for BW scoring."""
import pytest

from scoreSEND.scoring.bw import get_bw_score


def test_get_bw_score_requires_path_or_xpt():
    with pytest.raises(ValueError, match="path_db"):
        get_bw_score(studyid="x", path_db=None, xpt_dir=None)


def test_get_bw_score_requires_studyid_when_no_xpt():
    with pytest.raises(ValueError, match="studyid"):
        get_bw_score(studyid=None, path_db="/fake/db.db", xpt_dir=None)
