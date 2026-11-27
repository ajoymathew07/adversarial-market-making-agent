"""Checks that the package imports and the entry point runs."""

import mm
from mm.__main__ import main


def test_package_has_version():
    assert mm.__version__


def test_entry_point_runs(capsys):
    main()
    assert "scaffold OK" in capsys.readouterr().out
