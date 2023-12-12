import json
from pathlib import Path
from typing import List

import numpy as np
import numpy.typing as npt
import pytest
from pytest_benchmark.fixture import BenchmarkFixture

from py3dtiles.tilers.b3dm import wkb_utils
from py3dtiles.tilers.b3dm.wkb_utils import PolygonType

DATA_DIRECTORY = Path(__file__).parent / "fixtures"


@pytest.fixture
def clockwise_star() -> PolygonType:
    with open("tests/fixtures/star_clockwise.geojson") as f:
        star_geo = json.load(f)
        coords: PolygonType = star_geo["features"][0]["geometry"]["coordinates"]
        # triangulate expects the coordinates to be numpy array
        polygon = coords[0]
        for i in range(len(polygon)):
            polygon[i] = np.array(polygon[i], dtype=np.float32)
        # triangulate implicitly use wkb format, which is not self-closing
        del polygon[-1]
        return coords


@pytest.fixture
def counterclockwise_star() -> PolygonType:
    with open("tests/fixtures/star_counterclockwise.geojson") as f:
        star_geo = json.load(f)
        coords: PolygonType = star_geo["features"][0]["geometry"]["coordinates"]
        # triangulate expects the coordinates to be numpy array
        polygon = coords[0]
        for i in range(len(polygon)):
            polygon[i] = np.array(polygon[i], dtype=np.float32)
        # triangulate implicitly use wkb format, which is not self-closing
        del polygon[-1]
        return coords


@pytest.fixture
def counterclockwise_zx_star() -> PolygonType:
    with open("tests/fixtures/star_zx_counter_clockwise.geojson") as f:
        star_geo = json.load(f)
        coords: PolygonType = star_geo["features"][0]["geometry"]["coordinates"]
        # triangulate expects the coordinates to be numpy array
        polygon = coords[0]
        for i in range(len(polygon)):
            polygon[i] = np.array(polygon[i], dtype=np.float32)
        # triangulate implicitly use wkb format, which is not self-closing
        del polygon[-1]
        return coords


@pytest.fixture
def big_poly() -> PolygonType:
    with open("tests/fixtures/big_polygon_counter_clockwise.geojson") as f:
        big_poly = json.load(f)
        coords: PolygonType = big_poly["features"][0]["geometry"]["coordinates"]
        # triangulate expects the coordinates to be numpy array
        polygon = coords[0]
        for i in range(len(polygon)):
            polygon[i] = np.array(polygon[i], dtype=np.float32)
        # triangulate implicitly use wkb format, which is not self-closing
        del polygon[-1]
        return coords


@pytest.fixture
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


def test_triangulate_winding_order_simple() -> None:
    # simple case: a square on xy plane, counter-clockwise
    polygon = [
        [
            np.array([0, 0, 0], dtype=np.float32),
            np.array([1, 0, 0], dtype=np.float32),
            np.array([1, 1, 0], dtype=np.float32),
            np.array([0, 1, 0], dtype=np.float32),
        ]
    ]

    triangles = wkb_utils.triangulate(polygon)
    assert len(triangles[0]) == 2, "Should generate 2 triangles"
    assert all(
        np.cross(
            triangles[0][0][1] - triangles[0][0][0],
            triangles[0][0][2] - triangles[0][0][0],
        )
        == np.array([0, 0, 1], dtype=np.float32)
    ), "Check winding order is coherent with vertex order: counter-clockwise (triangle 1)"
    assert all(
        np.cross(
            triangles[0][1][1] - triangles[0][1][0],
            triangles[0][1][2] - triangles[0][1][0],
        )
        == np.array([0, 0, 1], dtype=np.float32)
    ), "Check winding order is coherent with vertex order: counter-clockwise (triangle 2)"

    # simple case 2: a square on xy plane, clockwise
    polygon = [
        [
            np.array([0, 0, 0], dtype=np.float32),
            np.array([0, 1, 0], dtype=np.float32),
            np.array([1, 1, 0], dtype=np.float32),
            np.array([1, 0, 0], dtype=np.float32),
        ]
    ]
    triangles = wkb_utils.triangulate(polygon)
    assert len(triangles[0]) == 2, "Should generate 2 triangles"
    assert all(
        np.cross(
            triangles[0][0][1] - triangles[0][0][0],
            triangles[0][0][2] - triangles[0][0][0],
        )
        == np.array([0, 0, -1], dtype=np.float32)
    ), "Check winding order is coherent with vertex order: clockwise (triangle1)"
    assert all(
        np.cross(
            triangles[0][1][1] - triangles[0][1][0],
            triangles[0][1][2] - triangles[0][1][0],
        )
        == np.array([0, 0, -1], dtype=np.float32)
    ), "Check winding order is coherent with vertex order: clockwise (triangle2)"


def test_triangulate_winding_order_complex(complex_polygon: PolygonType) -> None:
    triangles = wkb_utils.triangulate(complex_polygon)
    assert len(triangles[0]) == 3, "Should generate 2 triangles"
    crossprod_triangle1 = np.cross(
        triangles[0][0][1] - triangles[0][0][0], triangles[0][0][2] - triangles[0][0][0]
    )
    crossprod_triangle1 /= np.linalg.norm(crossprod_triangle1)
    assert all(
        crossprod_triangle1 == np.array([0, 0, 1], dtype=np.float32)
    ), "Check winding order is coherent with vertex order: counter-clockwise"


def test_triangulate_winding_order_stars(clockwise_star: PolygonType) -> None:
    triangles = wkb_utils.triangulate(clockwise_star)
    crossprod_triangle1 = np.cross(
        triangles[0][0][1] - triangles[0][0][0], triangles[0][0][2] - triangles[0][0][0]
    )
    crossprod_triangle1 /= np.linalg.norm(crossprod_triangle1)
    assert all(
        crossprod_triangle1 == np.array([0, 0, -1], dtype=np.float32)
    ), "Check winding order is coherent with vertex order: clockwise"


def test_triangulate_winding_order_counter_clockwise_stars(
    counterclockwise_star: PolygonType,
) -> None:
    triangles = wkb_utils.triangulate(counterclockwise_star)
    crossprod_triangle1 = np.cross(
        triangles[0][0][1] - triangles[0][0][0], triangles[0][0][2] - triangles[0][0][0]
    )
    crossprod_triangle1 /= np.linalg.norm(crossprod_triangle1)
    assert all(
        crossprod_triangle1 == np.array([0, 0, 1], dtype=np.float32)
    ), "Check winding order is coherent with vertex order: counter-clockwise"


def test_triangulate_winding_order_counter_clockwise_zx_stars(
    counterclockwise_zx_star: PolygonType,
) -> None:
    triangles = wkb_utils.triangulate(counterclockwise_zx_star)
    crossprod_triangle1 = np.cross(
        triangles[0][0][1] - triangles[0][0][0], triangles[0][0][2] - triangles[0][0][0]
    )
    crossprod_triangle1 /= np.linalg.norm(crossprod_triangle1)
    # check the 2nd dimension is the largest by far and is positive
    assert (
        crossprod_triangle1[1] > 0.8
    ), "Check winding order is coherent with vertex order: counter-clockwise in zx plane"


def test_big_poly_winding_order(big_poly: PolygonType) -> None:
    triangles = wkb_utils.triangulate(big_poly)
    crossprod_triangle1 = np.cross(
        triangles[0][0][1] - triangles[0][0][0], triangles[0][0][2] - triangles[0][0][0]
    )
    crossprod_triangle1 /= np.linalg.norm(crossprod_triangle1)
    assert all(
        crossprod_triangle1 == np.array([0, 0, 1], dtype=np.float32)
    ), "Check winding order is coherent with vertex order: counter-clockwise"


@pytest.mark.parametrize(
    "wkb_filename",
    # square_ewkb.wkb is marked as 'xfail' as py3dtiles does not support extended WKB yet
    ["square.wkb", pytest.param("square_ewkb.wkb", marks=pytest.mark.xfail)],
)
def test_parse_wkb(wkb_filename: str) -> None:
    expected_geom: List[List[List[npt.NDArray[np.float32]]]] = [
        [
            [
                np.array([0.0, 0.0, 0.0], dtype=np.float32),
                np.array([0.0, 10.0, 0.0], dtype=np.float32),
                np.array([10.0, 10.0, 0.0], dtype=np.float32),
                np.array([10.0, 0.0, 0.0], dtype=np.float32),
            ]
        ]
    ]
    with open(DATA_DIRECTORY / wkb_filename, "rb") as fobj:
        geom: List[List[List[npt.NDArray[np.float32]]]] = wkb_utils.parse(fobj.read())
        assert len(geom) == 1 and len(geom[0]) == 1
        # The following assertion fails for square_ewkb.wkb, due to parsing problem with the
        # Extended WKB version: we do not get a 3D-geom...
        assert np.all([np.all(g == e) for g, e in zip(geom[0][0], expected_geom[0][0])])


@pytest.mark.parametrize(
    "wkb_filename",
    # square_ewkb.wkb is marked as 'xfail' as py3dtiles does not support extended WKB yet
    ["square.wkb", pytest.param("square_ewkb.wkb", marks=pytest.mark.xfail)],
)
def test_triangle_soup_from_wkb(wkb_filename: str) -> None:
    with open(DATA_DIRECTORY / wkb_filename, "rb") as fobj:
        wkb_utils.TriangleSoup.from_wkb_multipolygon(fobj.read())


################
# benchmarking #
################
def test_benchmark_triangulate(
    complex_polygon: PolygonType, benchmark: BenchmarkFixture
) -> None:
    benchmark(wkb_utils.triangulate, complex_polygon)


def test_benchmark_star(
    clockwise_star: PolygonType, benchmark: BenchmarkFixture
) -> None:
    benchmark(wkb_utils.triangulate, clockwise_star)


def test_benchmark_big_poly(big_poly: PolygonType, benchmark: BenchmarkFixture) -> None:
    benchmark(wkb_utils.triangulate, big_poly)
