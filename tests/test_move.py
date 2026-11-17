import pytest

from posture.domain.move import interrupted


@pytest.mark.parametrize(
    ("height", "expected"),
    [(110.0, False), (109.2, False), (111.0, False), (108.9, True), (111.1, True)],
)
def test_interrupted(height: float, *, expected: bool) -> None:
    assert interrupted(height, 110.0) is expected
