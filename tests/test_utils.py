import numpy as np

from py3dtiles.utils import make_aabb_valid


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
