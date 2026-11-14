from enum import Enum, auto


class Stance(Enum):
    SITTING = auto()
    STANDING = auto()


def stance_for(height_cm: float, threshold_cm: float) -> Stance:
    # A Height exactly at the threshold counts as Standing so every Height has exactly one Stance.
    return Stance.STANDING if height_cm >= threshold_cm else Stance.SITTING
