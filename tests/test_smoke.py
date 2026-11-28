"""Checks that the package imports and the entry point runs."""

import mm
from mm.__main__ import main


def test_package_has_version():
    assert mm.__version__


def test_entry_point_prints_episode_summary(capsys):
    main()
    out = capsys.readouterr().out
    assert "Final PnL:" in out
    assert "Gate events:" in out
