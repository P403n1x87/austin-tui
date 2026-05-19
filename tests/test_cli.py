import sys
from contextlib import contextmanager


@contextmanager
def override_argv(args):
    original_argv = sys.argv
    sys.argv = args
    try:
        yield
    finally:
        sys.argv = original_argv


