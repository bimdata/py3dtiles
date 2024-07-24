import json
import multiprocessing
import os
import shutil
from contextlib import nullcontext
from pathlib import Path
from time import sleep
from typing import Union
from unittest.mock import patch

import laspy
import numpy as np
import plyfile
from _pytest.python_api import RaisesContext
from numpy.testing import assert_array_almost_equal, assert_array_equal
from pyproj import CRS
from pytest import mark, raises

from py3dtiles.convert import convert
from py3dtiles.exceptions import SrsInMissingException, SrsInMixinException
from py3dtiles.reader.ply_reader import create_plydata_with_renamed_property
from py3dtiles.tileset import TileSet, number_of_points_in_tileset
from py3dtiles.tileset.content import Pnts

DATA_DIRECTORY = Path(__file__).parent / "fixtures"


def test_convert(tmp_dir: Path) -> None:
    path = DATA_DIRECTORY / "ripple.las"
    convert(path, outfolder=tmp_dir)

    # basic asserts
    tileset_path = tmp_dir / "tileset.json"
    with tileset_path.open() as f:
        tileset = json.load(f)

    expecting_box = [5.0, 5.0, 0.8832, 5.0, 0, 0, 0, 5.0, 0, 0, 0, 0.8832]
    box = [round(value, 4) for value in tileset["root"]["boundingVolume"]["box"]]
    assert box == expecting_box

    assert Path(tmp_dir, "r0.pnts").exists()

    with laspy.open(path) as f:
        las_point_count = f.header.point_count

    assert las_point_count == number_of_points_in_tileset(tileset_path)


def test_convert_with_prune(tmp_dir: Path) -> None:
    # This file has 1 point at (-2, -2, -2) and 20001 at (1, 1, 1)
    # like this, it triggers the prune mechanism
    laz_path = DATA_DIRECTORY / "stacked_points.las"

    convert(
        laz_path,
        outfolder=tmp_dir,
        jobs=1,
        rgb=False,  # search bound cases by disabling rgb export
    )

    # basic asserts
    tileset_path = tmp_dir / "tileset.json"
    with tileset_path.open() as f:
        tileset = json.load(f)

    expecting_box = [1.5, 1.5, 1.5, 1.5, 0, 0, 0, 1.5, 0, 0, 0, 1.5]
    box = [round(value, 4) for value in tileset["root"]["boundingVolume"]["box"]]
    assert box == expecting_box

    assert Path(tmp_dir, "r0.pnts").exists()

    with laspy.open(laz_path) as f:
        las_point_count = f.header.point_count

    assert las_point_count == number_of_points_in_tileset(tileset_path)


def test_convert_without_srs(tmp_dir: Path) -> None:
    with raises(SrsInMissingException):
        convert(
            DATA_DIRECTORY / "without_srs.las",
            outfolder=tmp_dir,
            crs_out=CRS.from_epsg(4978),
            jobs=1,
        )
    assert not tmp_dir.exists()

    convert(
        DATA_DIRECTORY / "without_srs.las",
        outfolder=tmp_dir,
        crs_in=CRS.from_epsg(3949),
        crs_out=CRS.from_epsg(4978),
        jobs=1,
    )

    tileset_path = tmp_dir / "tileset.json"
    with tileset_path.open() as f:
        tileset = json.load(f)

    expecting_box = [0.9662, 0.0008, 0.7066, 0.9662, 0, 0, 0, 0.0024, 0, 0, 0, 0.7066]
    box = [round(value, 4) for value in tileset["root"]["boundingVolume"]["box"]]
    assert box == expecting_box

    assert Path(tmp_dir, "r.pnts").exists()

    with laspy.open(DATA_DIRECTORY / "without_srs.las") as f:
        las_point_count = f.header.point_count

    assert las_point_count == number_of_points_in_tileset(tileset_path)

    tile1 = Pnts.from_file(tmp_dir / "r0.pnts")
    assert tile1.body.feature_table.nb_points() == 1
    pt1_color = tile1.body.feature_table.get_feature_color_at(0)
    # Note the first point is taken as offset base
    if pt1_color is None:
        raise RuntimeError("pt1_color shouldn't be None.")
    assert_array_equal(pt1_color, np.array((187, 187, 187), dtype=np.uint8))


def test_convert_las_color_scale(tmp_dir: Path) -> None:
    convert(
        DATA_DIRECTORY / "without_srs.las",
        outfolder=tmp_dir,
        jobs=1,
    )

    tile1 = Pnts.from_file(tmp_dir / "r0.pnts")
    assert tile1.body.feature_table.nb_points() == 1
    pt1_color = tile1.body.feature_table.get_feature_color_at(0)
    if pt1_color is None:
        raise RuntimeError("pt1_color shouldn't be None.")
    assert_array_equal(pt1_color, np.array((187, 187, 187), dtype=np.uint8))
    convert(
        DATA_DIRECTORY / "without_srs.las",
        overwrite=True,
        color_scale=1.1,
        outfolder=tmp_dir,
        jobs=1,
    )
    tile1 = Pnts.from_file(tmp_dir / "r0.pnts")
    assert tile1.body.feature_table.nb_points() == 1
    pt1_color = tile1.body.feature_table.get_feature_color_at(0)
    # it should clamp to 255
    if pt1_color is None:
        raise RuntimeError("pt1_color shouldn't be None.")
    assert_array_equal(pt1_color, np.array((206, 206, 206), dtype=np.uint8))

    convert(
        DATA_DIRECTORY / "without_srs.las",
        overwrite=True,
        color_scale=1.5,
        outfolder=tmp_dir,
        jobs=1,
    )
    tile1 = Pnts.from_file(tmp_dir / "r0.pnts")
    assert tile1.body.feature_table.nb_points() == 1
    pt1_color = tile1.body.feature_table.get_feature_color_at(0)
    # it should clamp to 255
    if pt1_color is None:
        raise RuntimeError("pt1_color shouldn't be None.")
    assert_array_equal(pt1_color, np.array((255, 255, 255), dtype=np.uint8))


def test_convert_with_srs(tmp_dir: Path) -> None:
    convert(
        DATA_DIRECTORY / "with_srs_3857.las",
        outfolder=tmp_dir,
        crs_out=CRS.from_epsg(4978),
        jobs=1,
    )

    tileset_path = tmp_dir / "tileset.json"
    with tileset_path.open() as f:
        tileset = json.load(f)

    assert_array_almost_equal(
        tileset["root"]["transform"],
        [
            99.67987521469695,
            -7.9951492419151196,
            0.008110606960175354,
            0.0,
            4.123612711579332,
            51.49818036951855,
            85.6208691665381,
            0.0,
            -6.849693087091023,
            -85.34644109292454,
            51.66301092062502,
            0.0,
            -436496.4274249223,
            -5438698.662382579,
            3292223.375579676,
            1.0,
        ],
    )
    expecting_box = [
        5.1686,
        5.1834,
        0.1646,
        5.1684,
        0.0,
        0.0,
        0.0,
        5.1834,
        0.0,
        0.0,
        0.0,
        0.1952,
    ]
    box = [round(value, 4) for value in tileset["root"]["boundingVolume"]["box"]]
    assert box == expecting_box

    assert Path(tmp_dir, "r.pnts").exists()

    with laspy.open(DATA_DIRECTORY / "with_srs_3857.las") as f:
        las_point_count = f.header.point_count

    assert las_point_count == number_of_points_in_tileset(tileset_path)


def test_convert_simple_xyz(tmp_dir: Path) -> None:
    convert(
        DATA_DIRECTORY / "simple.xyz",
        outfolder=tmp_dir,
        crs_in=CRS.from_epsg(3857),
        crs_out=CRS.from_epsg(4978),
        jobs=1,
    )
    assert Path(tmp_dir, "tileset.json").exists()
    assert Path(tmp_dir, "r.pnts").exists()

    xyz_point_count = 0
    with open(DATA_DIRECTORY / "simple.xyz") as f:
        while line := f.readline():
            xyz_point_count += 1 if line != "" else 0

    tileset_path = tmp_dir / "tileset.json"
    assert xyz_point_count == number_of_points_in_tileset(tileset_path)

    with tileset_path.open() as f:
        tileset = json.load(f)

    expecting_box = [0.3916, 0.3253, -0.0001, 0.39, 0, 0, 0, 0.3099, 0, 0, 0, 0.0001]
    box = [round(value, 4) for value in tileset["root"]["boundingVolume"]["box"]]
    assert box == expecting_box


def test_convert_xyz_rgb_i_c(tmp_dir: Path) -> None:
    convert(
        DATA_DIRECTORY / "simple_with_irgb_and_classification.csv",
        outfolder=tmp_dir,
        jobs=1,
    )
    assert Path(tmp_dir, "tileset.json").exists()
    assert Path(tmp_dir, "r.pnts").exists()

    xyz_point_count = -1  # compensate for header line
    with open(DATA_DIRECTORY / "simple_with_irgb_and_classification.csv") as f:
        while line := f.readline():
            xyz_point_count += 1 if line != "" else 0

    tileset_path = tmp_dir / "tileset.json"
    assert xyz_point_count == number_of_points_in_tileset(tileset_path)

    tileset = TileSet.from_file(tmp_dir / "tileset.json")
    tile_content = Pnts.from_file(tmp_dir / "r.pnts")
    ft_body = tile_content.body.feature_table.body
    # assert position
    world_coords = tileset.root_tile.transform_coords(ft_body.position.reshape(-1, 3))
    assert_array_equal(
        world_coords,
        np.array(
            [
                [281345.9, 369123.25, 0.0],
                [281345.12, 369123.47, 0.0],
                [281345.56, 369123.88, 0.0],
            ],
            dtype=np.float32,
        ),
    )
    assert ft_body.color is not None
    assert_array_equal(ft_body.color, [0, 0, 200, 10, 0, 0, 0, 10, 0])
    # batch table
    bt = tile_content.body.batch_table
    assert_array_equal(bt.get_binary_property("Intensity"), [3, 1, 2])
    assert_array_equal(bt.get_binary_property("Classification"), [22, 21, 22])


def test_convert_xyz_rgb_i_c_with_srs(tmp_dir: Path) -> None:
    convert(
        DATA_DIRECTORY / "simple_with_irgb_and_classification.csv",
        outfolder=tmp_dir,
        crs_in=CRS.from_epsg(28992),
        crs_out=CRS.from_epsg(4978),
        jobs=1,
    )
    assert Path(tmp_dir, "tileset.json").exists()
    assert Path(tmp_dir, "r.pnts").exists()

    xyz_point_count = -1  # compensate for header line
    with open(DATA_DIRECTORY / "simple_with_irgb_and_classification.csv") as f:
        while line := f.readline():
            xyz_point_count += 1 if line != "" else 0

    tileset_path = tmp_dir / "tileset.json"
    assert xyz_point_count == number_of_points_in_tileset(tileset_path)


def test_convert_xyz_with_rgb(tmp_dir: Path) -> None:
    convert(DATA_DIRECTORY / "simple_with_rgb.xyz", outfolder=tmp_dir)

    tile1 = Pnts.from_file(tmp_dir / "r0.pnts")
    assert tile1.body.feature_table.nb_points() == 1
    pt1_color = tile1.body.feature_table.get_feature_color_at(0)
    # Note the first point is taken as offset base
    if pt1_color is None:
        raise RuntimeError("pt1_color shouldn't be None.")
    assert_array_equal(pt1_color, np.array((10, 0, 0), dtype=np.uint8))

    tile2 = Pnts.from_file(tmp_dir / "r4.pnts")
    assert tile2.body.feature_table.nb_points() == 1
    pt2_color = tile2.body.feature_table.get_feature_color_at(0)
    # Note the first point is taken as offset base
    if pt2_color is None:
        raise RuntimeError("pt2_color shouldn't be None.")
    assert_array_equal(pt2_color, np.array((0, 0, 200), dtype=np.uint8))

    tile3 = Pnts.from_file(tmp_dir / "r6.pnts")
    assert tile3.body.feature_table.nb_points() == 1
    pt3_color = tile3.body.feature_table.get_feature_color_at(0)
    # Note the first point is taken as offset base
    if pt3_color is None:
        raise RuntimeError("pt3_color shouldn't be None.")
    assert_array_equal(pt3_color, np.array((0, 10, 0), dtype=np.uint8))


def test_convert_xyz_with_rgb_color_scale(tmp_dir: Path) -> None:
    convert(DATA_DIRECTORY / "simple_with_rgb.xyz", outfolder=tmp_dir, color_scale=1.5)

    tile1 = Pnts.from_file(tmp_dir / "r0.pnts")
    assert tile1.body.feature_table.nb_points() == 1
    pt1_color = tile1.body.feature_table.get_feature_color_at(0)
    # Note the first point is taken as offset base
    if pt1_color is None:
        raise RuntimeError("pt1_color shouldn't be None.")
    assert_array_equal(pt1_color, np.array((15, 0, 0), dtype=np.uint8))

    tile2 = Pnts.from_file(tmp_dir / "r4.pnts")
    assert tile2.body.feature_table.nb_points() == 1
    pt2_color = tile2.body.feature_table.get_feature_color_at(0)
    # Note the first point is taken as offset base
    if pt2_color is None:
        raise RuntimeError("pt2_color shouldn't be None.")
    assert_array_equal(pt2_color, np.array((0, 0, 255), dtype=np.uint8))

    tile3 = Pnts.from_file(tmp_dir / "r6.pnts")
    assert tile3.body.feature_table.nb_points() == 1
    pt3_color = tile3.body.feature_table.get_feature_color_at(0)
    # Note the first point is taken as offset base
    if pt3_color is None:
        raise RuntimeError("pt3_color shouldn't be None.")
    assert_array_equal(pt3_color, np.array((0, 15, 0), dtype=np.uint8))


def test_convert_ply(tmp_dir: Path) -> None:
    convert(DATA_DIRECTORY / "simple.ply", outfolder=tmp_dir, jobs=1)
    assert Path(tmp_dir, "tileset.json").exists()
    assert Path(tmp_dir, "r.pnts").exists()

    expected_point_count = 22300
    tileset_path = tmp_dir / "tileset.json"
    assert expected_point_count == number_of_points_in_tileset(tileset_path)

    with tileset_path.open() as f:
        tileset = json.load(f)

    expecting_box = [
        4.5437,
        5.5984,
        1.1842,
        4.5437,
        0.0,
        0.0,
        0.0,
        5.5984,
        0.0,
        0.0,
        0.0,
        1.1842,
    ]
    box = [round(value, 4) for value in tileset["root"]["boundingVolume"]["box"]]
    assert box == expecting_box

    tile1 = Pnts.from_file(tmp_dir / "r0.pnts")
    assert tile1.body.feature_table.nb_points() == 5293
    pt1_color = tile1.body.feature_table.get_feature_color_at(0)
    if pt1_color is None:
        raise RuntimeError("pt1_color shouldn't be None.")
    assert_array_equal(pt1_color, np.array((0, 0, 0), dtype=np.uint8))


def test_convert_ply_with_color(tmp_dir: Path) -> None:
    # 8 bits color
    convert(DATA_DIRECTORY / "simple_with_8_bits_colors.ply", outfolder=tmp_dir, jobs=1)
    assert Path(tmp_dir, "tileset.json").exists()
    assert Path(tmp_dir, "r.pnts").exists()

    expected_point_count = 4
    tileset_path = tmp_dir / "tileset.json"
    assert expected_point_count == number_of_points_in_tileset(tileset_path)

    tile1 = Pnts.from_file(tmp_dir / "r0.pnts")
    assert tile1.body.feature_table.nb_points() == 1
    pt1_color = tile1.body.feature_table.get_feature_color_at(0)
    if pt1_color is None:
        raise RuntimeError("pt1_color shouldn't be None.")
    assert_array_equal(pt1_color, np.array((0, 128, 0), dtype=np.uint8))

    tile1 = Pnts.from_file(tmp_dir / "r3.pnts")
    assert tile1.body.feature_table.nb_points() == 1
    pt1_color = tile1.body.feature_table.get_feature_color_at(0)
    if pt1_color is None:
        raise RuntimeError("pt1_color shouldn't be None.")
    assert_array_equal(pt1_color, np.array((10, 0, 0), dtype=np.uint8))

    tile1 = Pnts.from_file(tmp_dir / "r5.pnts")
    assert tile1.body.feature_table.nb_points() == 1
    pt1_color = tile1.body.feature_table.get_feature_color_at(0)
    if pt1_color is None:
        raise RuntimeError("pt1_color shouldn't be None.")
    assert_array_equal(pt1_color, np.array((0, 0, 20), dtype=np.uint8))

    tile1 = Pnts.from_file(tmp_dir / "r6.pnts")
    assert tile1.body.feature_table.nb_points() == 1
    pt1_color = tile1.body.feature_table.get_feature_color_at(0)
    if pt1_color is None:
        raise RuntimeError("pt1_color shouldn't be None.")
    assert_array_equal(pt1_color, np.array((40, 40, 40), dtype=np.uint8))

    # 16 bits colors
    # every value should be divided by 256
    convert(
        DATA_DIRECTORY / "simple_with_16_bits_colors.ply",
        outfolder=tmp_dir,
        jobs=1,
        overwrite=True,
    )
    assert Path(tmp_dir, "tileset.json").exists()
    assert Path(tmp_dir, "r.pnts").exists()

    expected_point_count = 4
    tileset_path = tmp_dir / "tileset.json"
    assert expected_point_count == number_of_points_in_tileset(tileset_path)

    tile1 = Pnts.from_file(tmp_dir / "r0.pnts")
    assert tile1.body.feature_table.nb_points() == 1
    pt1_color = tile1.body.feature_table.get_feature_color_at(0)
    if pt1_color is None:
        raise RuntimeError("pt1_color shouldn't be None.")
    assert_array_equal(pt1_color, np.array((0, 0, 0), dtype=np.uint8))

    tile1 = Pnts.from_file(tmp_dir / "r3.pnts")
    assert tile1.body.feature_table.nb_points() == 1
    pt1_color = tile1.body.feature_table.get_feature_color_at(0)
    if pt1_color is None:
        raise RuntimeError("pt1_color shouldn't be None.")
    assert_array_equal(pt1_color, np.array((1, 0, 0), dtype=np.uint8))

    tile1 = Pnts.from_file(tmp_dir / "r5.pnts")
    assert tile1.body.feature_table.nb_points() == 1
    pt1_color = tile1.body.feature_table.get_feature_color_at(0)
    if pt1_color is None:
        raise RuntimeError("pt1_color shouldn't be None.")
    assert_array_equal(pt1_color, np.array((0, 0, 4), dtype=np.uint8))

    tile1 = Pnts.from_file(tmp_dir / "r6.pnts")
    assert tile1.body.feature_table.nb_points() == 1
    pt1_color = tile1.body.feature_table.get_feature_color_at(0)
    if pt1_color is None:
        raise RuntimeError("pt1_color shouldn't be None.")
    assert_array_equal(pt1_color, np.array((255, 255, 255), dtype=np.uint8))


def test_convert_ply_with_color_scale(tmp_dir: Path) -> None:
    # 8 bits color
    convert(
        DATA_DIRECTORY / "simple_with_8_bits_colors.ply",
        outfolder=tmp_dir,
        jobs=1,
        color_scale=3,
    )
    assert Path(tmp_dir, "tileset.json").exists()
    assert Path(tmp_dir, "r.pnts").exists()

    tile1 = Pnts.from_file(tmp_dir / "r0.pnts")
    assert tile1.body.feature_table.nb_points() == 1
    pt1_color = tile1.body.feature_table.get_feature_color_at(0)
    if pt1_color is None:
        raise RuntimeError("pt1_color shouldn't be None.")
    assert_array_equal(pt1_color, np.array((0, 255, 0), dtype=np.uint8))

    tile1 = Pnts.from_file(tmp_dir / "r3.pnts")
    assert tile1.body.feature_table.nb_points() == 1
    pt1_color = tile1.body.feature_table.get_feature_color_at(0)
    if pt1_color is None:
        raise RuntimeError("pt1_color shouldn't be None.")
    assert_array_equal(pt1_color, np.array((30, 0, 0), dtype=np.uint8))

    tile1 = Pnts.from_file(tmp_dir / "r5.pnts")
    assert tile1.body.feature_table.nb_points() == 1
    pt1_color = tile1.body.feature_table.get_feature_color_at(0)
    if pt1_color is None:
        raise RuntimeError("pt1_color shouldn't be None.")
    assert_array_equal(pt1_color, np.array((0, 0, 60), dtype=np.uint8))

    tile1 = Pnts.from_file(tmp_dir / "r6.pnts")
    assert tile1.body.feature_table.nb_points() == 1
    pt1_color = tile1.body.feature_table.get_feature_color_at(0)
    if pt1_color is None:
        raise RuntimeError("pt1_color shouldn't be None.")
    assert_array_equal(pt1_color, np.array((120, 120, 120), dtype=np.uint8))


def test_convert_ply_with_wrong_classification(tmp_dir: Path) -> None:
    # Buggy feature name, classification is lost.
    convert(
        DATA_DIRECTORY / "simple.ply",
        outfolder=tmp_dir,
        jobs=1,
        classification=True,
    )
    assert Path(tmp_dir, "tileset.json").exists()
    assert Path(tmp_dir, "r.pnts").exists()

    for py3dt_file in tmp_dir.iterdir():
        if py3dt_file.suffix != ".pnts":
            continue
        tile_content = Pnts.from_file(py3dt_file)
        assert "Classification" in tile_content.body.batch_table.header.data
        assert np.array_equal(
            np.unique(tile_content.body.batch_table.body.data[0]),
            np.array([0], dtype=np.uint8),  # classification is lost
        )


def test_convert_ply_with_good_classification(tmp_dir: Path) -> None:
    EXPECTED_LABELS = np.array([0, 1, 2, -1], dtype=np.uint8)
    # Change the classification property name in the tested .ply file
    ply_data = plyfile.PlyData.read(DATA_DIRECTORY / "simple.ply")
    ply_data = create_plydata_with_renamed_property(ply_data, "label", "classification")
    modified_ply_filename = DATA_DIRECTORY / "modified.ply"
    ply_data.write(modified_ply_filename)
    # Valid feature name, classification is preserved.
    convert(
        modified_ply_filename,
        outfolder=tmp_dir,
        jobs=1,
        classification=True,
    )
    assert Path(tmp_dir, "tileset.json").exists()
    assert Path(tmp_dir, "r.pnts").exists()

    tileset_labels = np.array((), dtype=np.uint8)
    for py3dt_file in tmp_dir.iterdir():
        if py3dt_file.suffix != ".pnts":
            continue
        tile_content = Pnts.from_file(py3dt_file)
        assert "Classification" in tile_content.body.batch_table.header.data
        pnts_labels = np.unique(tile_content.body.batch_table.body.data[0])
        # classification is OK for each pnts
        assert np.all([labels in EXPECTED_LABELS for labels in pnts_labels])
        tileset_labels = np.unique(np.append(tileset_labels, pnts_labels))
    # Every label is encountered in the global tileset
    assert np.array_equal(tileset_labels, EXPECTED_LABELS)
    # Clean the test directory
    modified_ply_filename.unlink()


def test_convert_ply_with_intensity(tmp_dir: Path) -> None:
    # Valid feature name, intensity is preserved.
    convert(
        DATA_DIRECTORY / "simple_with_intensity.ply",
        outfolder=tmp_dir,
        jobs=1,
        intensity=True,
    )
    assert Path(tmp_dir, "tileset.json").exists()
    assert Path(tmp_dir, "r.pnts").exists()

    tile_content = Pnts.from_file(tmp_dir / "r.pnts")
    assert_array_equal(
        tile_content.body.feature_table.body.position,
        [0, 0, 0, 1, 1, 0, 1, 0, 1, 0, 1, 1],
    )
    assert "Intensity" in tile_content.body.batch_table.header.data
    assert_array_equal(
        [80, 129, 15, 90],
        tile_content.body.batch_table.get_binary_property("Intensity"),
    )


def test_convert_ply_with_classification_and_intensity(tmp_dir: Path) -> None:
    # Valid feature name, intensity is preserved.
    convert(
        DATA_DIRECTORY / "simple_with_classification_and_intensity.ply",
        outfolder=tmp_dir,
        jobs=1,
        intensity=True,
    )
    assert Path(tmp_dir, "tileset.json").exists()
    assert Path(tmp_dir, "r.pnts").exists()

    tile_content = Pnts.from_file(tmp_dir / "r.pnts")
    assert_array_equal(
        tile_content.body.feature_table.body.position,
        [0, 0, 0, 1, 1, 0, 1, 0, 1, 0, 1, 1],
    )
    assert "Classification" in tile_content.body.batch_table.header.data
    assert_array_equal(
        [1, 2, 2, 1],
        tile_content.body.batch_table.get_binary_property("Classification"),
    )
    assert "Intensity" in tile_content.body.batch_table.header.data
    assert_array_equal(
        [80, 129, 15, 90],
        tile_content.body.batch_table.get_binary_property("Intensity"),
    )


def test_convert_ply_with_classification_and_intensity_f4(tmp_dir: Path) -> None:
    # we don't support arbitrary precision in intensity yet, but the conversion should succeed with warnings
    convert(
        DATA_DIRECTORY / "simple_with_classification_and_intensity_f4.ply",
        outfolder=tmp_dir,
        jobs=1,
        intensity=True,
    )

    # without intensity
    convert(
        DATA_DIRECTORY / "simple_with_classification_and_intensity_f4.ply",
        outfolder=tmp_dir,
        jobs=1,
        intensity=False,
        overwrite=True,
    )
    assert Path(tmp_dir, "tileset.json").exists()
    assert Path(tmp_dir, "r.pnts").exists()

    tile_content = Pnts.from_file(tmp_dir / "r.pnts")
    assert_array_equal(
        tile_content.body.feature_table.body.position,
        [0, 0, 0, 1, 1, 0, 1, 0, 1, 0, 1, 1],
    )
    assert "Classification" in tile_content.body.batch_table.header.data
    assert_array_equal(
        [1, 2, 2, 1],
        tile_content.body.batch_table.get_binary_property("Classification"),
    )
    assert "Intensity" not in tile_content.body.batch_table.header.data


def test_convert_mix_las_xyz(tmp_dir: Path) -> None:
    convert(
        [DATA_DIRECTORY / "simple.xyz", DATA_DIRECTORY / "with_srs_3857.las"],
        outfolder=tmp_dir,
        crs_out=CRS.from_epsg(4978),
        jobs=1,
    )
    assert Path(tmp_dir, "tileset.json").exists()
    assert Path(tmp_dir, "r.pnts").exists()

    xyz_point_count = 0
    with open(DATA_DIRECTORY / "simple.xyz") as f:
        while line := f.readline():
            xyz_point_count += 1 if line != "" else 0

    with laspy.open(DATA_DIRECTORY / "with_srs_3857.las") as f:
        las_point_count = f.header.point_count

    tileset_path = tmp_dir / "tileset.json"
    assert xyz_point_count + las_point_count == number_of_points_in_tileset(
        tileset_path
    )

    with tileset_path.open() as f:
        tileset = json.load(f)

    expecting_box = [
        3415.9824,
        5513.0671,
        -20917.9692,
        44316.7617,
        0.0,
        0.0,
        0.0,
        14858.1809,
        0.0,
        0.0,
        0.0,
        1585.8657,
    ]
    box = [round(value, 4) for value in tileset["root"]["boundingVolume"]["box"]]
    assert box == expecting_box


def test_convert_mix_input_crs(tmp_dir: Path) -> None:
    with raises(SrsInMixinException):
        convert(
            [
                DATA_DIRECTORY / "with_srs_3950.las",
                DATA_DIRECTORY / "with_srs_3857.las",
            ],
            outfolder=tmp_dir,
            crs_out=CRS.from_epsg(4978),
            jobs=1,
        )
    assert not tmp_dir.exists()

    with raises(SrsInMixinException):
        convert(
            [
                DATA_DIRECTORY / "with_srs_3950.las",
                DATA_DIRECTORY / "with_srs_3857.las",
            ],
            outfolder=tmp_dir,
            crs_in=CRS.from_epsg(3432),
            crs_out=CRS.from_epsg(4978),
            jobs=1,
        )
    assert not tmp_dir.exists()

    convert(
        [DATA_DIRECTORY / "with_srs_3950.las", DATA_DIRECTORY / "with_srs_3857.las"],
        outfolder=tmp_dir,
        crs_in=CRS.from_epsg(3432),
        crs_out=CRS.from_epsg(4978),
        force_crs_in=True,
        jobs=1,
    )
    assert tmp_dir.exists()


@mark.skipif(
    multiprocessing.get_start_method() != "fork",
    reason="'patch' function works only with the multiprocessing 'fork' method (not available on windows).",
)
def test_convert_xyz_exception_in_run(tmp_dir: Path) -> None:
    with patch("py3dtiles.reader.xyz_reader.run") as mock_run, raises(
        Exception,
        match="An exception occurred in a worker: builtins.Exception: Exception in run",
    ):
        # NOTE: this is intentionnally different from below, we are testing 2 different things
        # Here, we test that a very early fail wont block the run, and that it will terminate correctly
        mock_run.side_effect = Exception("Exception in run")
        convert(
            DATA_DIRECTORY / "simple.xyz",
            outfolder=tmp_dir,
            crs_in=CRS.from_epsg(3857),
            crs_out=CRS.from_epsg(4978),
        )


@mark.skipif(
    multiprocessing.get_start_method() != "fork",
    reason="'patch' function works only with the multiprocessing 'fork' method (not available on windows).",
)
def test_convert_las_exception_in_run(tmp_dir: Path) -> None:
    with patch("py3dtiles.reader.las_reader.run") as mock_run, raises(
        Exception,
        match="An exception occurred in a worker: builtins.Exception: Exception in run",
    ):

        def side_effect(*args):  # type: ignore
            sleep(1)
            raise Exception("Exception in run")

        mock_run.side_effect = side_effect
        convert(
            DATA_DIRECTORY / "with_srs_3857.las",
            outfolder=tmp_dir,
            crs_in=CRS.from_epsg(3857),
            crs_out=CRS.from_epsg(4978),
        )


def test_convert_export_folder_already_exists(tmp_dir: Path) -> None:
    assert not (tmp_dir / "tileset.json").exists()
    assert len(os.listdir(tmp_dir)) == 0

    # folder is empty, ok
    convert(
        DATA_DIRECTORY / "simple.xyz",
        outfolder=tmp_dir,
        jobs=1,
    )

    shutil.rmtree(tmp_dir)
    # folder will be created
    convert(
        DATA_DIRECTORY / "simple.xyz",
        outfolder=tmp_dir,
        jobs=1,
    )
    assert tmp_dir.exists()
    assert (tmp_dir / "tileset.json").exists()

    # now, subsequent conversion will fail
    with raises(
        FileExistsError, match=f"Folder '{tmp_dir}' already exists and is not empty."
    ):
        convert(
            DATA_DIRECTORY / "simple.xyz",
            outfolder=tmp_dir,
            jobs=1,
        )

    # but overwriting works
    convert(
        DATA_DIRECTORY / "simple.xyz",
        outfolder=tmp_dir,
        overwrite=True,
        jobs=1,
    )

    assert (tmp_dir / "tileset.json").exists()

    # finally, one file in folder is enough to bail
    shutil.rmtree(tmp_dir)
    tmp_dir.touch()
    with raises(
        FileExistsError,
        match=f"'{tmp_dir}' already exists and is not a directory. Not deleting it.",
    ):
        convert(
            DATA_DIRECTORY / "simple.xyz",
            outfolder=tmp_dir,
            jobs=1,
        )
    tmp_dir.unlink()


def test_convert_many_point_same_location(tmp_dir: Path) -> None:
    # This is how the file has been generated.
    xyz_path = tmp_dir / "pc_with_many_points_at_same_location.xyz"
    xyz_data = np.concatenate(
        (np.random.random((10000, 3)), np.repeat([[0, 0, 0]], repeats=20000, axis=0))
    )
    with xyz_path.open("w") as f:
        np.savetxt(f, xyz_data, delimiter=" ", fmt="%.10f")

    convert(xyz_path, outfolder=tmp_dir / "tiles")

    tileset_path = tmp_dir / "tiles" / "tileset.json"
    assert number_of_points_in_tileset(tileset_path) == 30000


@mark.parametrize(
    "rgb_bool,classif_bool",
    [(True, True), (False, True), (True, False), (False, False)],
)
def test_convert_rgb_classif(rgb_bool: bool, classif_bool: bool, tmp_dir: Path) -> None:
    expected_raise: Union[nullcontext[None], RaisesContext[ValueError]]
    if not classif_bool:
        expected_raise = raises(
            ValueError, match="The property Classification is not found"
        )
    else:
        # Ideally one does not raise if classification is required but pytest won't implement such
        # a feature (see https://github.com/pytest-dev/pytest/issues/1830). This solution is
        # suggested by a comment in this thread (see
        # https://github.com/pytest-dev/pytest/issues/1830#issuecomment-425653756).
        expected_raise = nullcontext()

    input_filepath = DATA_DIRECTORY / "simple_with_classification.ply"
    convert(
        input_filepath, rgb=rgb_bool, classification=classif_bool, outfolder=tmp_dir
    )

    assert Path(tmp_dir, "r.pnts").exists()

    ply_data = plyfile.PlyData.read(input_filepath)
    ply_point_count = ply_data.elements[0].count

    assert ply_point_count == number_of_points_in_tileset(tmp_dir / "tileset.json")

    tileset = TileSet.from_file(tmp_dir / "tileset.json")
    for tile_content in tileset.get_all_tile_contents():
        if isinstance(tile_content, TileSet):
            continue

        assert rgb_bool ^ (tile_content.body.feature_table.body.color is None)
        with expected_raise:
            bt_prop = tile_content.body.batch_table.get_binary_property(
                "Classification"
            )
            assert len(bt_prop) > 0
