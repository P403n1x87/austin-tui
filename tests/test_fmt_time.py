import pytest

from austin_tui.adapters import fmt_time


@pytest.mark.parametrize(
    "us, expected",
    [
        (0, "0.00s"),
        (500_000, "0.50s"),
        (1_000_000, "1.00s"),
        (59_000_000, "59.00s"),
        (60_000_000, "01m00s"),
        (61_000_000, "01m01s"),
        (90_500_000, "01m30s"),
        (3_600_000_000, "60m00s"),
        (3_661_000_000, "61m01s"),
    ],
)
def test_fmt_time(us: int, expected: str) -> None:
    assert fmt_time(us) == expected
