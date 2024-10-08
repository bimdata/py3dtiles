import unittest
from pathlib import Path

import numpy as np
from numpy.testing import assert_array_equal

from py3dtiles.tileset.content import Pnts, PntsHeader, read_binary_tile_content
from py3dtiles.tileset.content.pnts_feature_table import (
    PntsFeatureTableHeader,
    SemanticPoint,
)


class TestTileContentReader(unittest.TestCase):
    def test_read(self) -> None:
        tile = Pnts.from_file(Path("tests/fixtures/pointCloudRGB.pnts"))

        self.assertEqual(tile.header.version, 1.0)
        self.assertEqual(tile.header.tile_byte_length, 15176)
        self.assertEqual(tile.header.ft_json_byte_length, 148)
        self.assertEqual(tile.header.ft_bin_byte_length, 15000)
        self.assertEqual(tile.header.bt_json_byte_length, 0)
        self.assertEqual(tile.header.bt_bin_byte_length, 0)

        feature_table = tile.body.feature_table
        pt_color = feature_table.get_feature_color_at(0)
        if pt_color is None:
            raise RuntimeError("pt_color should not be None")
        assert_array_equal(
            np.array([44, 243, 209], dtype=np.uint8),
            pt_color,
        )

    def test_str(self) -> None:
        tile_content = read_binary_tile_content(
            Path("tests/fixtures/pointCloudRGB.pnts")
        )
        expected_string_components = [
            "------ Tile header ------",
            "magic: b'pnts'",
            "version: 1",
            "tile_byte_length: 15176",
            "json_feature_table_length: 148",
            "bin_feature_table_length: 15000",
            "json_batch_table_length: 0",
            "bin_batch_table_length: 0",
            "------ Tile body ------",
            "feature_table_header: {'"
            "POINTS_LENGTH': 1000"
            ", 'RTC_CENTER': [1215012.8828876738, -4736313.051199594, 4081605.22126042]"
            ", 'POSITION': {'byteOffset': 0}, 'RGB': {'byteOffset': 12000}}",
            "points_length: 1000",
            "first_point_position: [ 2.19396     4.489685   -0.17107764]",
            "first_point_color: [ 44 243 209]",
            "first_point_normal: None",
        ]
        string_components = str(tile_content).split("\n")
        for expected_line, line in zip(expected_string_components, string_components):
            assert expected_line == line


class TestTileBuilder(unittest.TestCase):
    def test_build_without_colors(self) -> None:
        tread = Pnts.from_file(Path("tests/fixtures/pointCloudRGB.pnts"))
        feature_0_position = tread.body.feature_table.get_feature_position_at(0)

        # create features
        positions = []
        for i in range(tread.body.feature_table.header.points_length):
            feature_position = tread.body.feature_table.get_feature_position_at(i)
            positions.append(feature_position)
        position_array = np.array(positions).flatten()

        # create a tile
        feature_table_header = PntsFeatureTableHeader.from_semantic(
            SemanticPoint.POSITION,
            None,
            None,
            len(positions),
        )
        t = Pnts.from_features(feature_table_header, position_array)

        # configure the tile
        rtc = (1215012.8828876738, -4736313.051199594, 4081605.22126042)
        t.body.feature_table.header.rtc = rtc

        # get an array
        tile_arr = t.to_array()
        t2 = Pnts.from_array(tile_arr)
        self.assertEqual(t2.header.version, 1.0)

        # Test the tile byte length
        self.assertEqual(t2.header.tile_byte_length, 12152)
        self.assertEqual(
            t2.header.tile_byte_length % 8, 0
        )  # tile bytes must be 8-byte aligned

        # Test the feature table byte lengths
        json_feature_table_end = PntsHeader.BYTE_LENGTH + t2.header.ft_json_byte_length
        self.assertEqual(json_feature_table_end % 8, 0)
        self.assertEqual(t2.header.ft_json_byte_length, 124)
        bin_feature_table_end = json_feature_table_end + t2.header.ft_bin_byte_length
        self.assertEqual(bin_feature_table_end % 8, 0)
        self.assertEqual(t2.header.ft_bin_byte_length, 12000)

        self.assertEqual(t2.header.bt_json_byte_length, 0)
        self.assertEqual(t2.header.bt_bin_byte_length, 0)

        feature_table = t.body.feature_table

        assert_array_equal(feature_0_position, feature_table.get_feature_position_at(0))

    def test_build(self) -> None:
        tread = Pnts.from_file(Path("tests/fixtures/pointCloudRGB.pnts"))

        # create features
        positions = []
        colors = []
        for i in range(tread.body.feature_table.header.points_length):
            (
                feature_position,
                feature_color,
                _,
            ) = tread.body.feature_table.get_feature_at(i)
            positions.append(feature_position)
            colors.append(feature_color)
        position_array = np.array(positions).flatten()
        color_array = np.array(colors).flatten()

        # create a tile
        feature_table_header = PntsFeatureTableHeader.from_semantic(
            SemanticPoint.POSITION, SemanticPoint.RGB, None, len(positions)
        )
        t = Pnts.from_features(feature_table_header, position_array, color_array)

        # configure the tile
        rtc = (1215012.8828876738, -4736313.051199594, 4081605.22126042)
        t.body.feature_table.header.rtc = rtc

        # get an array
        tile_arr = t.to_array()
        t2 = Pnts.from_array(tile_arr)
        self.assertEqual(t2.header.version, 1.0)

        # Test the tile byte length
        self.assertEqual(t2.header.tile_byte_length, 15176)
        self.assertEqual(
            t2.header.tile_byte_length % 8, 0
        )  # tile bytes must be 8-byte aligned

        # Test the feature table byte lengths
        json_feature_table_end = PntsHeader.BYTE_LENGTH + t2.header.ft_json_byte_length
        self.assertEqual(json_feature_table_end % 8, 0)
        self.assertEqual(t2.header.ft_json_byte_length, 148)
        bin_feature_table_end = json_feature_table_end + t2.header.ft_bin_byte_length
        self.assertEqual(bin_feature_table_end % 8, 0)
        self.assertEqual(t2.header.ft_bin_byte_length, 15000)

        self.assertEqual(t2.header.bt_json_byte_length, 0)
        self.assertEqual(t2.header.bt_bin_byte_length, 0)

        feature_table = t.body.feature_table
        pt_color = feature_table.get_feature_color_at(0)
        if pt_color is None:
            raise RuntimeError("pt_color should not be None")
        assert_array_equal(
            np.array([44, 243, 209], dtype=np.uint8),
            pt_color,
        )
