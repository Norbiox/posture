from posture.domain.stance import Stance, stance_for


def test_below_threshold_is_sitting() -> None:
    assert stance_for(70.0, 90.0) is Stance.SITTING


def test_at_threshold_is_standing() -> None:
    assert stance_for(90.0, 90.0) is Stance.STANDING


def test_above_threshold_is_standing() -> None:
    assert stance_for(110.0, 90.0) is Stance.STANDING
