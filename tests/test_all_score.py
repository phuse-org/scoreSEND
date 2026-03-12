"""Tests for get_all_score."""
import pytest

from scoreSEND.all_score import get_all_score


def test_get_all_score_requires_studyid_when_no_xpt():
    with pytest.raises(ValueError, match="studyid"):
        get_all_score(studyid=None, path_db="/fake/db.db")


def test_get_all_score_domain_check():
    with pytest.raises(ValueError, match="domain"):
        get_all_score(studyid="x", path_db="/fake/db.db", domain=["invalid"])
