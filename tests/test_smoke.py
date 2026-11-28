"""Checks that the package imports and the entry point runs."""

import mm
from mm.__main__ import main


def test_package_has_version():
    assert mm.__version__


def test_entry_point_prints_evaluation_summary(capsys, tmp_path):
    main(["--seeds", "dev", "--scenarios", "base", "--steps", "50", "--out", str(tmp_path)])
    out = capsys.readouterr().out
    assert "Final PnL" in out
    assert "% time at limit" in out
