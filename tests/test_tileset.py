from __future__ import annotations

import json
from pathlib import Path

from py3dtiles.tileset import Tile, TileSet

DATA_DIRECTORY = Path(__file__).parent / "fixtures"


def test_constructor() -> None:
    tile_set = TileSet()
    assert tile_set.asset.to_dict() == {"version": "1.0"}
    assert tile_set.extensions == {}
    assert tile_set.geometric_error == 500
    assert isinstance(tile_set.root_tile, Tile)


def test_to_dict(tileset: TileSet) -> None:
    assert tileset.to_dict() == {
        "root": {
            "boundingVolume": {
                "box": [
                    1.0,
                    2.0,
                    3.0,
                    4.0,
                    5.0,
                    6.0,
                    7.0,
                    8.0,
                    9.0,
                    10.0,
                    11.0,
                    12.0,
                ]
            },
            "geometricError": 3.14159,
            "refine": "ADD",
        },
        "extensions": {"Test": {}},
        "extensionsUsed": ["Test"],
        "geometricError": 500,
        "asset": {"version": "1.0"},
    }


def test_from_dict(tmp_dir_with_content: Path) -> None:

    assert Path(tmp_dir_with_content, "tileset.json").exists()
    assert Path(tmp_dir_with_content, "r.pnts").exists()

    with (tmp_dir_with_content / "tileset.json").open() as f:
        tileset_dict = json.load(f)

    tileset = TileSet.from_dict(tileset_dict)
    tileset.root_uri = tmp_dir_with_content

    assert tileset.to_dict() == tileset_dict


def test_delete_on_disk(tileset_on_disk_with_sub_tileset_path: Path) -> None:
    # This test only checks if delete_on_disk doesn't delete sub-tileset

    tmp_folder = tileset_on_disk_with_sub_tileset_path.parent
    assert (tmp_folder / "tileset.json").exists()
    assert (tmp_folder / "upper_tileset.json").exists()

    tileset = TileSet.from_file(tileset_on_disk_with_sub_tileset_path)
    tileset.delete_on_disk(tmp_folder / "upper_tileset.json")

    assert (tmp_folder / "tileset.json").exists()
    assert (tmp_folder / "r.pnts").exists()
    assert not (tmp_folder / "upper_tileset.json").exists()


def test_delete_on_disk_with_sub_tileset(
    tileset_on_disk_with_sub_tileset_path: Path,
) -> None:
    # This test manly checks if delete_on_disk removes correctly all tile contents (binary and sub tileset)

    tmp_folder = tileset_on_disk_with_sub_tileset_path.parent
    assert (tmp_folder / "tileset.json").exists()
    assert (tmp_folder / "upper_tileset.json").exists()

    tileset = TileSet.from_file(tileset_on_disk_with_sub_tileset_path)
    tileset.delete_on_disk(tmp_folder / "upper_tileset.json", delete_sub_tileset=True)

    assert not (tmp_folder / "tileset.json").exists()
    assert not (tmp_folder / "r.pnts").exists()
    assert not (tmp_folder / "upper_tileset.json").exists()
