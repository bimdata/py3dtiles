import shutil
from pathlib import Path

import numpy as np
from pytest import raises

from py3dtiles.utils import make_aabb_valid, mkdir_or_raise


def test_make_aabb_valid() -> None:
    aabb = np.array([[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]])
    make_aabb_valid(aabb)
    np.testing.assert_array_equal(aabb, np.array([[0, 0, 0], [1.0, 1.0, 1.0]]))
    aabb = np.array([[0, 0, 0], [0, 0, 0]], dtype=np.float64)
    make_aabb_valid(aabb)
    np.testing.assert_array_equal(
        aabb, np.array([[0, 0, 0], [0.00001, 0.00001, 0.00001]])
    )
    aabb = np.array([[9, 10, 11], [9, 10, 11]], dtype=np.float64)
    make_aabb_valid(aabb)
    np.testing.assert_array_equal(
        aabb, np.array([[9, 10, 11], [9.00001, 10.00001, 11.00001]])
    )
    aabb = np.array([[9, 12, 14], [10, 13, 15]], dtype=np.float64)
    make_aabb_valid(aabb)
    np.testing.assert_array_equal(aabb, np.array([[9, 12, 14], [10, 13, 15]]))
    aabb = np.array([[9, 12, 14], [9, 13, 15]], dtype=np.float64)
    make_aabb_valid(aabb)
    np.testing.assert_array_equal(aabb, np.array([[9, 12, 14], [9.00001, 13, 15]]))


def test_mkdir_or_raise(tmp_dir: Path) -> None:
    mkdir_or_raise(tmp_dir)
    (tmp_dir / "foo").touch()

    with raises(
        FileExistsError, match=f"Folder '{tmp_dir}' already exists and is not empty."
    ):
        mkdir_or_raise(tmp_dir)

    mkdir_or_raise(tmp_dir, overwrite=True)
    assert len(list(tmp_dir.iterdir())) == 0

    shutil.rmtree(tmp_dir)

    mkdir_or_raise(tmp_dir)
    # second time, should still succeed because it is empty
    mkdir_or_raise(tmp_dir)

    shutil.rmtree(tmp_dir)
    # it is now a file
    tmp_dir.touch()

    with raises(
        FileExistsError,
        match=f"'{tmp_dir}' already exists and is not a directory. Not deleting it.",
    ):
        mkdir_or_raise(tmp_dir)
    tmp_dir.unlink()
