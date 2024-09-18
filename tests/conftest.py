import copy
import json
import shutil
from pathlib import Path
from typing import Any, Dict, Generator

import numpy as np
import plyfile
from pyproj import CRS
from pytest import fixture

from py3dtiles.convert import convert
from py3dtiles.tilers.b3dm.wkb_utils import PolygonType
from py3dtiles.tilers.point.node import Grid, Node
from py3dtiles.tileset import BoundingVolumeBox, Tile, TileSet
from py3dtiles.tileset.extension.batch_table_hierarchy_extension import (
    BatchTableHierarchy,
)
from py3dtiles.utils import compute_spacing

from .fixtures.mock_extension import MockExtension

DATA_DIRECTORY = Path(__file__).parent / "fixtures"


@fixture
def tmp_dir() -> Generator[Path, None, None]:
    tmp_dir = Path("tmp/")
    tmp_dir.mkdir()
    yield tmp_dir
    if tmp_dir.exists():
        if tmp_dir.is_dir():
            shutil.rmtree(tmp_dir, ignore_errors=True)
        else:
            tmp_dir.unlink()


@fixture
def tmp_dir_with_content(tmp_dir: Path) -> Generator[Path, None, None]:
    tileset_folder = tmp_dir / "simple_xyz"
    convert(DATA_DIRECTORY / "simple.xyz", outfolder=tileset_folder, overwrite=True)
    yield tileset_folder


@fixture
def tileset_path_1(tmp_dir: Path) -> Generator[Path, None, None]:
    tileset_folder = tmp_dir / "1"
    convert(
        DATA_DIRECTORY / "with_srs_3857.las",
        crs_out=CRS.from_epsg(3950),
        outfolder=tileset_folder,
    )
    yield tileset_folder / "tileset.json"


@fixture
def tileset_1(tileset_path_1: Path) -> TileSet:
    tileset = TileSet.from_file(tileset_path_1)
    tileset.root_tile.get_or_fetch_content(tileset_path_1.parent)
    return tileset


@fixture
def tileset_path_2(tmp_dir: Path) -> Generator[Path, None, None]:
    tileset_folder = tmp_dir / "2"
    convert(DATA_DIRECTORY / "with_srs_3950.las", outfolder=tileset_folder)
    yield tileset_folder / "tileset.json"


@fixture
def tileset_2(tileset_path_2: Path) -> TileSet:
    tileset = TileSet.from_file(tileset_path_2)
    tileset.root_tile.get_or_fetch_content(tileset_path_2.parent)
    return tileset


@fixture
def ply_filepath() -> Generator[Path, None, None]:
    yield DATA_DIRECTORY / "simple.ply"


@fixture
def buggy_ply_filepath() -> Generator[Path, None, None]:
    yield DATA_DIRECTORY / "buggy.ply"


@fixture(params=["wrongname", "vertex"])
def buggy_ply_data(request) -> Generator[Dict[str, Any], None, None]:  # type: ignore [no-untyped-def]
    """This ply data does not contain any 'vertex' element!"""
    types = [("x", np.float32, (5,)), ("y", np.float32, (5,)), ("z", np.float32, (5,))]
    data = [(np.random.sample(5), np.random.sample(5), np.random.sample(5))]
    if request.param == "wrongname":
        arr = np.array(data, dtype=np.dtype(types))
    else:
        arr = np.array([data[0][:2]], np.dtype(types[:2]))
    ply_item = plyfile.PlyElement.describe(data=arr, name=request.param)
    ply_data = plyfile.PlyData(elements=[ply_item])
    yield {
        "data": ply_data,
        "msg": "vertex" if request.param == "wrongname" else "x, y, z",
    }


@fixture
def node() -> Node:
    bbox = np.array([[0, 0, 0], [2, 2, 2]])
    return Node(b"noeud", bbox, compute_spacing(bbox))


@fixture
def grid(node: Node) -> Grid:
    return Grid(node)


@fixture
def tileset() -> TileSet:
    """
    Programmatically define a tileset sample encountered in the
    TileSet json header specification cf
    https://github.com/AnalyticalGraphicsInc/3d-tiles/tree/master/specification#tileset-json
    :return: a TileSet object.
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


@fixture
def tileset_on_disk_with_sub_tileset_path(tmp_dir: Path) -> Generator[Path, None, None]:
    convert(DATA_DIRECTORY / "simple.xyz", outfolder=tmp_dir, overwrite=True)

    sub_tileset_path = tmp_dir / "tileset.json"
    main_tileset_path = tmp_dir / "upper_tileset.json"
    sub_tileset = TileSet.from_file(sub_tileset_path)

    tileset = TileSet()
    tileset.root_tile.content_uri = Path("tileset.json")
    tileset.root_tile.bounding_volume = copy.deepcopy(
        sub_tileset.root_tile.bounding_volume
    )
    tileset.root_tile.transform = copy.deepcopy(sub_tileset.root_tile.transform)
    tileset.write_as_json(main_tileset_path)

    yield main_tileset_path


@fixture
def batch_table_hierarchy_reference_file() -> Path:
    return DATA_DIRECTORY / "batch_table_hierarchy_reference_sample.json"


@fixture
def batch_table_hierarchy_with_indexes() -> BatchTableHierarchy:
    """
    Programmatically define the reference sample encountered in the
    BTH specification cf
    https://github.com/AnalyticalGraphicsInc/3d-tiles/tree/master/extensions/3DTILES_batch_table_hierarchy#batch-table-json-schema-updates
    :return: the sample as BatchTableHierarchy object.
    """
    bth = BatchTableHierarchy()

    wall_class = bth.add_class("Wall", ["color"])
    wall_class.add_instance({"color": "white"}, [6])
    wall_class.add_instance({"color": "red"}, [6, 10, 11])
    wall_class.add_instance({"color": "yellow"}, [7, 11])
    wall_class.add_instance({"color": "gray"}, [7])
    wall_class.add_instance({"color": "brown"}, [8])
    wall_class.add_instance({"color": "black"}, [8])

    building_class = bth.add_class("Building", ["name", "address"])
    building_class.add_instance({"name": "unit29", "address": "100 Main St"}, [10])
    building_class.add_instance({"name": "unit20", "address": "102 Main St"}, [10])
    building_class.add_instance({"name": "unit93", "address": "104 Main St"}, [9])

    owner_class = bth.add_class("Owner", ["type", "id"])
    owner_class.add_instance({"type": "city", "id": 1120})
    owner_class.add_instance({"type": "resident", "id": 1250})
    owner_class.add_instance({"type": "commercial", "id": 6445})
    return bth


@fixture
def batch_table_hierarchy_with_instances() -> BatchTableHierarchy:
    bth = BatchTableHierarchy()

    wall_class = bth.add_class("Wall", ["color"])
    building_class = bth.add_class("Building", ["name", "address"])
    owner_class = bth.add_class("Owner", ["type", "id"])

    owner_city = owner_class.add_instance({"type": "city", "id": 1120})
    owner_resident = owner_class.add_instance({"type": "resident", "id": 1250})
    owner_commercial = owner_class.add_instance({"type": "commercial", "id": 6445})

    building_29 = building_class.add_instance(
        {"name": "unit29", "address": "100 Main St"}, [owner_resident]
    )
    building_20 = building_class.add_instance(
        {"name": "unit20", "address": "102 Main St"}, [owner_resident]
    )
    building_93 = building_class.add_instance(
        {"name": "unit93", "address": "104 Main St"}, [owner_city]
    )

    wall_class.add_instance({"color": "white"}, [building_29])
    wall_class.add_instance(
        {"color": "red"}, [building_29, owner_resident, owner_commercial]
    )
    wall_class.add_instance({"color": "yellow"}, [building_20, owner_commercial])
    wall_class.add_instance({"color": "gray"}, [building_20])
    wall_class.add_instance({"color": "brown"}, [building_93])
    wall_class.add_instance({"color": "black"}, [building_93])
    return bth


@fixture
def clockwise_star() -> PolygonType:
    with open(DATA_DIRECTORY / "star_clockwise.geojson") as f:
        star_geo = json.load(f)
        coords: PolygonType = star_geo["features"][0]["geometry"]["coordinates"]
        # triangulate expects the coordinates to be numpy array
        polygon = coords[0]
        for i in range(len(polygon)):
            polygon[i] = np.array(polygon[i], dtype=np.float32)
        # triangulate implicitly use wkb format, which is not self-closing
        del polygon[-1]
        return coords


@fixture
def counterclockwise_star() -> PolygonType:
    with open(DATA_DIRECTORY / "star_counterclockwise.geojson") as f:
        star_geo = json.load(f)
        coords: PolygonType = star_geo["features"][0]["geometry"]["coordinates"]
        # triangulate expects the coordinates to be numpy array
        polygon = coords[0]
        for i in range(len(polygon)):
            polygon[i] = np.array(polygon[i], dtype=np.float32)
        # triangulate implicitly use wkb format, which is not self-closing
        del polygon[-1]
        return coords


@fixture
def counterclockwise_zx_star() -> PolygonType:
    with open(DATA_DIRECTORY / "star_zx_counter_clockwise.geojson") as f:
        star_geo = json.load(f)
        coords: PolygonType = star_geo["features"][0]["geometry"]["coordinates"]
        # triangulate expects the coordinates to be numpy array
        polygon = coords[0]
        for i in range(len(polygon)):
            polygon[i] = np.array(polygon[i], dtype=np.float32)
        # triangulate implicitly use wkb format, which is not self-closing
        del polygon[-1]
        return coords


@fixture
def big_poly() -> PolygonType:
    with open(DATA_DIRECTORY / "big_polygon_counter_clockwise.geojson") as f:
        big_poly = json.load(f)
        coords: PolygonType = big_poly["features"][0]["geometry"]["coordinates"]
        # triangulate expects the coordinates to be numpy array
        polygon = coords[0]
        for i in range(len(polygon)):
            polygon[i] = np.array(polygon[i], dtype=np.float32)
        # triangulate implicitly use wkb format, which is not self-closing
        del polygon[-1]
        return coords


@fixture
def complex_polygon() -> PolygonType:
    # tricky polygon 1:
    # 0x---------x 4
    #   \        |
    #    \       |
    #   1 x      |
    #    /       |
    #   /        |
    # 2x---------x 3
    # the first few vertices seems to indicate an inverse winding order
    return [
        [
            np.array([0, 1, 0], dtype=np.float32),
            np.array([0.5, 0.5, 0], dtype=np.float32),
            np.array([0, 0, 0], dtype=np.float32),
            np.array([1, 0, 0], dtype=np.float32),
            np.array([1, 1, 0], dtype=np.float32),
        ]
    ]
