"""Test the point cloud readers.

The example that is run in the test (`simple.ply`) comes from the [CGAL repository](https://github.com/CGAL/cgal/blob/master/Data/data/points_3/b9_training.ply). Thanks to their maintainers (for more details, please refer to CGAL, Computational Geometry Algorithms Library, https://www.cgal.org):

"""

from pathlib import Path
from typing import Any, Dict

import numpy as np
import plyfile
from pytest import raises

from py3dtiles.reader import ply_reader


def test_ply_get_metadata(ply_filepath: Path) -> None:
    ply_metadata = ply_reader.get_metadata(path=ply_filepath)
    expected_point_count = 22300
    expected_aabb = (
        np.array([5.966480625e05, 2.43620015625e05, 7.350153350830078e01]),
        np.array([5.967389375e05, 2.43731984375e05, 9.718580627441406e01]),
    )
    assert list(ply_metadata.keys()) == [
        "portions",
        "aabb",
        "crs_in",
        "point_count",
        "avg_min",
    ]
    assert ply_metadata["portions"] == [(str(ply_filepath), (0, expected_point_count))]
    assert np.all(ply_metadata["aabb"][0] == expected_aabb[0])
    assert np.all(ply_metadata["aabb"][1] == expected_aabb[1])
    assert ply_metadata["crs_in"] is None
    assert ply_metadata["point_count"] == expected_point_count
    assert np.all(ply_metadata["avg_min"] == expected_aabb[0])


def test_ply_get_metadata_buggy(
    buggy_ply_data: Dict[str, Any], buggy_ply_filepath: Path
) -> None:
    buggy_ply_data["data"].write(buggy_ply_filepath)
    with raises(KeyError, match=buggy_ply_data["msg"]):
        _ = ply_reader.get_metadata(path=buggy_ply_filepath)
    buggy_ply_filepath.unlink()


def test_create_plydata_with_renamed_property(ply_filepath: Path) -> None:
    ply_data = plyfile.PlyData.read(ply_filepath)
    modified_ply_data = ply_reader.create_plydata_with_renamed_property(
        ply_data, "label", "classification"
    )
    for prop1, prop2 in zip(
        ply_data["vertex"].properties, modified_ply_data["vertex"].properties
    ):
        assert prop1.name == prop2.name or (
            prop1.name == "label" and prop2.name == "classification"
        )
    for dtype1, dtype2 in zip(
        ply_data["vertex"].data.dtype.names,
        modified_ply_data["vertex"].data.dtype.names,
    ):
        assert dtype1 == dtype2 or (dtype1 == "label" and dtype2 == "classification")
