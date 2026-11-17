# The Desk stops a few millimetres from its target; a larger gap means the move was cut short.
ARRIVAL_TOLERANCE_CM = 1.0


def interrupted(height_cm: float, target_cm: float) -> bool:
    return abs(height_cm - target_cm) > ARRIVAL_TOLERANCE_CM
