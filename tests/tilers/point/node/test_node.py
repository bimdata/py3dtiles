from pathlib import Path

import numpy as np
from numpy.testing import assert_array_equal

from py3dtiles.tilers.point.node.node import split_tileset
from py3dtiles.tileset.bounding_volume_box import BoundingVolumeBox
from py3dtiles.tileset.tile import Tile
from py3dtiles.tileset.tileset import TileSet


def test_split_tileset(tmp_dir: Path) -> None:
    tile = Tile(geometric_error=1234)
    tile.bounding_volume = BoundingVolumeBox.from_points(
        [np.array([1, 2, 4]), np.array([4, 8, 0])]
    )
    tile.set_refine_mode("REPLACE")

    split_tileset(tile, "split", tmp_dir)
    assert tile.children == []
    assert tile.content_uri == Path("tileset.split.json")

    tileset_path = tmp_dir / "tileset.split.json"
    assert tileset_path.exists()
    ts = TileSet.from_file(tileset_path)
    assert ts.root_tile.geometric_error == 1234
    # these 3 lines are *mainly* to make mypy happy
    assert isinstance(ts.root_tile.bounding_volume, BoundingVolumeBox)
    assert ts.root_tile.bounding_volume._box is not None
    assert tile.bounding_volume._box is not None

    assert_array_equal(ts.root_tile.bounding_volume._box, tile.bounding_volume._box)
    # sure about this one?
    assert ts.root_tile.get_refine_mode() == "ADD"
