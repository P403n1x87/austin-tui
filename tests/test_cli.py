import sys
from contextlib import contextmanager

import pytest

from austin_tui.__main__ import main


@contextmanager
def override_argv(args):
    original_argv = sys.argv
    sys.argv = args
    try:
        yield
    finally:
        sys.argv = original_argv


def test_main_no_args(capsys):
    with pytest.raises(SystemExit) as e, override_argv(["austin-tui"]):
        main()
    assert e.value.code == -1
    assert "No PID" in capsys.readouterr().err
