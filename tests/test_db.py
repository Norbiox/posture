from typing import TYPE_CHECKING

from posture.db import Db

if TYPE_CHECKING:
    from pathlib import Path


def test_presets_are_listed_highest_first(tmp_path: Path) -> None:
    db = Db(tmp_path / "posture.db")
    db.add_preset("b-low", 65.0)
    db.add_preset("a-low", 65.0)

    presets = db.list_presets()
    heights = [p.height_cm for p in presets]
    assert heights == sorted(heights, reverse=True)
    assert [p.name for p in presets if p.height_cm == 65.0] == ["a-low", "b-low"]
