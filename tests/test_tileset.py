from __future__ import annotations

import json
from pathlib import Path
import shutil
import unittest

from py3dtiles.convert import convert
from py3dtiles.tileset import BoundingVolumeBox, Tile, TileSet
from py3dtiles.tileset.extension import BaseExtension
from py3dtiles.typing import ExtensionDictType

DATA_DIRECTORY = Path(__file__).parent / "fixtures"


class MockExtension(BaseExtension):
    @classmethod
    def from_dict(cls, extension_dict: ExtensionDictType) -> MockExtension:
        return cls("MockExtension")

    def to_dict(self) -> ExtensionDictType:
        return {}


class TestTileSet(unittest.TestCase):
    @classmethod
    def build_sample(cls):
        """
        Programmatically define a tileset sample encountered in the
        TileSet json header specification cf
        https://github.com/AnalyticalGraphicsInc/3d-tiles/tree/master/specification#tileset-json
        :return: the sample as TileSet object.
        """
        tile_set = TileSet()
        bounding_volume = BoundingVolumeBox()
        bounding_volume.set_from_list([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12])
        root_tile = Tile(geometric_error=3.14159, bounding_volume=bounding_volume)
        # Setting the mode to the default mode does not really change things.
        # The following line is thus just here ot test the "callability" of
        # set_refine_mode():
        root_tile.set_refine_mode("ADD")
        tile_set.root_tile = root_tile

        extension = MockExtension("Test")
        tile_set.extensions[extension.name] = extension
        tile_set.extensions_used.add(extension.name)

        return tile_set

    def test_constructor(self):
        tile_set = TileSet()
        self.assertDictEqual(tile_set.asset.to_dict(), {"version": "1.0"})
        self.assertDictEqual(tile_set.extensions, {})
        self.assertEqual(tile_set.geometric_error, 500)
        self.assertIsNotNone(tile_set.root_tile)

    def test_to_dict(self):
        self.assertDictEqual(
            self.build_sample().to_dict(),
            {
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
            },
        )

    def test_from_dict(self):
        tmp_dir = Path("tmp/")
        tmp_dir.mkdir(exist_ok=True)

        convert(DATA_DIRECTORY / "simple.xyz", outfolder=tmp_dir, overwrite=True)

        assert Path(tmp_dir, "tileset.json").exists()
        assert Path(tmp_dir, "r.pnts").exists()

        with (tmp_dir / "tileset.json").open() as f:
            tileset_dict = json.load(f)

        tileset = TileSet.from_dict(tileset_dict)
        tileset.root_uri = tmp_dir

        self.assertDictEqual(tileset.to_dict(), tileset_dict)

        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
