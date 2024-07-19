import math
import unittest
from typing import List

import numpy as np
from numpy.testing import assert_array_almost_equal, assert_array_equal

from py3dtiles.tileset import BoundingVolumeBox

# fmt: off
DUMMY_MATRIX = [
    1, 2, 3, 4,
    5, 6, 7, 8,
    9, 10, 11, 12,
]
# fmt: on


class TestBoundingVolumeBox(unittest.TestCase):
    @classmethod
    def build_box_sample(cls) -> BoundingVolumeBox:
        bounding_volume_box = BoundingVolumeBox()
        bounding_volume_box.set_from_list(DUMMY_MATRIX)
        return bounding_volume_box

    def test_constructor(self) -> None:
        bounding_volume_box = BoundingVolumeBox()
        self.assertIs(bounding_volume_box._box, None)

    def test_from_list(self) -> None:
        bounding_volume_box = BoundingVolumeBox.from_list(DUMMY_MATRIX)
        box = bounding_volume_box._box
        assert_array_equal(box, np.array(DUMMY_MATRIX))  # type: ignore [arg-type]

    def test_set_from_list(self) -> None:
        bounding_volume_box = BoundingVolumeBox()
        bounding_volume_box.set_from_list(DUMMY_MATRIX)
        box = bounding_volume_box._box
        assert_array_equal(box, np.array(DUMMY_MATRIX))  # type: ignore [arg-type]

    def test_set_from_invalid_list(self) -> None:
        bounding_volume_box = BoundingVolumeBox()

        # Empty list
        bounding_volume_list: List[float] = []
        with self.assertRaises(ValueError):
            bounding_volume_box.set_from_list(bounding_volume_list)
        self.assertIs(bounding_volume_box._box, None)

        # Too small list
        with self.assertRaises(ValueError):
            bounding_volume_box.set_from_list(DUMMY_MATRIX[:-1])
        self.assertIs(bounding_volume_box._box, None)

        # Too long list
        with self.assertRaises(ValueError):
            bounding_volume_box.set_from_list(DUMMY_MATRIX + [13])
        self.assertIs(bounding_volume_box._box, None)

        # Not only number
        with self.assertRaises(ValueError):
            bounding_volume_box.set_from_list(DUMMY_MATRIX[:-1] + ["a"])
        self.assertIs(bounding_volume_box._box, None)

        with self.assertRaises(ValueError):
            bounding_volume_box.set_from_list(DUMMY_MATRIX[:-1] + [[1]])
        self.assertIs(bounding_volume_box._box, None)

    def test_from_points(self) -> None:
        bounding_volume_box = BoundingVolumeBox.from_points(
            [np.array([1, 0, 0]), np.array([2, 0, 0])]
        )
        assert bounding_volume_box._box is not None
        assert_array_equal(
            bounding_volume_box._box, np.array([1.5, 0, 0, 0.5, 0, 0, 0, 0, 0, 0, 0, 0])
        )

    def test_set_from_points(self) -> None:
        bounding_volume_box = BoundingVolumeBox()
        bounding_volume_box.set_from_points([np.array([1, 0, 0]), np.array([2, 0, 0])])
        assert bounding_volume_box._box is not None
        assert_array_equal(
            bounding_volume_box._box, np.array([1.5, 0, 0, 0.5, 0, 0, 0, 0, 0, 0, 0, 0])
        )

        bounding_volume_box = BoundingVolumeBox()
        bounding_volume_box.set_from_points(
            [
                np.array([1, 0, 0]),
                np.array([2, 0, 0]),
                np.array([1, 1, 1]),
                np.array([2, 0, -1]),
            ]
        )
        assert bounding_volume_box._box is not None
        assert_array_equal(
            bounding_volume_box._box, [1.5, 0.5, 0, 0.5, 0, 0, 0, 0.5, 0, 0, 0, 1]
        )

    def test_set_from_invalid_points(self) -> None:
        # what if I give only one point ?
        pass

    def test_get_center(self) -> None:
        bounding_volume_box = BoundingVolumeBox()
        with self.assertRaises(AttributeError):
            bounding_volume_box.get_center()

        bounding_volume_box = TestBoundingVolumeBox.build_box_sample()
        assert_array_equal(bounding_volume_box.get_center(), [1, 2, 3])

    def test_translate(self) -> None:
        bounding_volume_box = BoundingVolumeBox()
        with self.assertRaises(AttributeError):
            bounding_volume_box.translate(np.array([-1, -2, -3]))

        bounding_volume_box = TestBoundingVolumeBox.build_box_sample()
        assert_array_equal(bounding_volume_box.get_center(), [1, 2, 3])

        bounding_volume_box.translate(np.array([-1, -2, -3]))
        # Should move only the center
        # fmt: off
        expected_result = [
            0, 0, 0, 4,
            5, 6, 7, 8,
            9, 10, 11, 12,
        ]
        # fmt: on
        box = bounding_volume_box._box
        assert_array_equal(box, expected_result)  # type: ignore [arg-type]

    def test_transform(self) -> None:
        bounding_volume_box = TestBoundingVolumeBox.build_box_sample()

        # Assert box hasn't change after transformation with identity matrix
        transformer = np.identity(4)
        bounding_volume_box.transform(transformer)
        assert_array_equal(bounding_volume_box._box, DUMMY_MATRIX)  # type: ignore [arg-type]

        # Assert box is translated by [10, 10, 10] on X,Y, Z axis
        transformer[:, 3] = 10
        bounding_volume_box.transform(transformer)
        # fmt: off
        expected_result = [
            11, 12, 13, 4,
            5, 6, 7, 8,
            9, 10, 11, 12,
        ]
        # fmt: on
        assert_array_equal(bounding_volume_box._box, expected_result)  # type: ignore [arg-type]

        # 90° rotation on z axis
        theta = math.pi / 2
        c, s = np.cos(theta), np.sin(theta)
        # fmt: off
        transformer = np.array(
            ((c, -s, 0, 0),
             (s, c, 0, 0),
             (0, 0, 1, 0),
             (0, 0, 0, 1))
        )
        # fmt: on
        bounding_volume_box = BoundingVolumeBox()
        bounding_volume_box.set_from_list([0, 0, 0, 1, 0, 0, 0, 2, 0, 0, 0, 3])
        bounding_volume_box.transform(transformer)
        assert bounding_volume_box._box is not None
        # fmt: off
        assert_array_almost_equal(
            bounding_volume_box._box,
            [
                # same center
                0, 0, 0,
                # x,y half axis inverted
                0, 1, 0,
                -2, 0, 0,
                # same z half axis
                0, 0, 3,
            ],
        )
        # fmt: on

        # 45° rotation y axis
        theta = math.pi / 4
        c, s = np.cos(theta), np.sin(theta)
        transformer = np.array(
            # fmt: off
            ((c, 0, -s, 0),
             (0, 1, 0, 0),
             (s, 0, c, 0),
             (0, 0, 0, 1))
            # fmt: on
        )
        bounding_volume_box = BoundingVolumeBox()
        bounding_volume_box.set_from_list([0, 0, 0, 1, 0, 0, 0, 2, 0, 0, 0, 3])
        bounding_volume_box.transform(transformer)
        assert bounding_volume_box._box is not None
        assert_array_almost_equal(
            bounding_volume_box._box,
            # fmt: off
            [
                # same center
                0, 0, 0,
                # x axis
                c, 0, s,
                # y unchanged
                0, 2, 0,
                -3 * c, 0, 3 * s,
            ],
            # fmt: on
        )

        # -30° deg rotation on x axis
        theta = -math.pi / 3
        c, s = np.cos(theta), np.sin(theta)
        # fmt: off
        transformer = np.array(
            ((1, 0, 0, 0),
             (0, c, -s, 0),
             (0, s, c, 0),
             (0, 0, 0, 1))
        )
        # fmt: on
        bounding_volume_box = BoundingVolumeBox()
        bounding_volume_box.set_from_list([0, 0, 0, 1, 0, 0, 0, 2, 0, 0, 0, 3])
        bounding_volume_box.transform(transformer)
        assert bounding_volume_box._box is not None
        assert_array_almost_equal(
            bounding_volume_box._box,
            # fmt: off
            [
                # same center
                0, 0, 0,
                # x axis unchanged,
                1, 0, 0,
                0, 2 * c, 2 * s,
                0, -3 * s, 3 * c,
            ],
            # fmt: on
        )

    def test_get_corners(self) -> None:
        bounding_volume_box = BoundingVolumeBox()
        with self.assertRaises(AttributeError):
            bounding_volume_box.get_corners()

        bounding_volume_box = TestBoundingVolumeBox.build_box_sample()
        assert_array_equal(
            bounding_volume_box.get_corners(),
            [  # almost a kindness test
                [-20, -22, -24],
                [-12, -12, -12],
                [-6, -6, -6],
                [2, 4, 6],
                [0, 0, 0],
                [8, 10, 12],
                [14, 16, 18],
                [22, 26, 30],
            ],
        )

    def test_get_canonical_as_array(self) -> None:
        pass

    def test_to_dict(self) -> None:
        bounding_volume_box = BoundingVolumeBox()
        with self.assertRaises(AttributeError):
            bounding_volume_box.to_dict()

        self.assertDictEqual(
            TestBoundingVolumeBox.build_box_sample().to_dict(),
            {"box": DUMMY_MATRIX},
        )


if __name__ == "__main__":
    unittest.main()
