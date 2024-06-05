from __future__ import annotations

from typing import TYPE_CHECKING

from numba import njit  # type: ignore
from numba.typed import List
import numpy as np

from py3dtiles.utils import aabb_size_to_subdivision_type, SubdivisionType
from .distance import is_point_far_enough, xyz_to_key

if TYPE_CHECKING:
    from .node import Node


# BIMDATA - ajout de l'input dip
@njit(fastmath=True, cache=True)
def _insert(
    cells_xyz,
    cells_rgb,
    cells_dip,
    aabmin,
    inv_aabb_size,
    cell_count,
    xyz,
    rgb,
    dip,
    spacing,
    shift,
    force=False,
):
    keys = xyz_to_key(xyz, cell_count, aabmin, inv_aabb_size, shift)

    if force:
        # allocate this one once and for all
        for k in np.unique(keys):
            idx = np.where(keys - k == 0)
            cells_xyz[k] = np.concatenate((cells_xyz[k], xyz[idx]))
            cells_rgb[k] = np.concatenate((cells_rgb[k], rgb[idx]))
            # BIMDATA - ajout de cells_dip
            cells_dip[k] = np.concatenate((cells_dip[k], dip[idx]))
    else:
        notinserted = np.full(len(xyz), False)
        needs_balance = False

        for i in range(len(xyz)):
            k = keys[i]
            if cells_xyz[k].shape[0] == 0 or is_point_far_enough(
                cells_xyz[k], xyz[i], spacing
            ):
                cells_xyz[k] = np.concatenate((cells_xyz[k], xyz[i].reshape(1, 3)))
                cells_rgb[k] = np.concatenate((cells_rgb[k], rgb[i].reshape(1, 3)))
                # BIMDATA -ajout de cells_dip
                cells_dip[k] = np.concatenate((cells_dip[k], dip[i].reshape(1, 3)))
                if cell_count[0] < 8:
                    needs_balance = needs_balance or cells_xyz[k].shape[0] > 200000
            else:
                notinserted[i] = True

        # BIMDATA - Ajout de l'output dip
        return xyz[notinserted], rgb[notinserted], dip[notinserted], needs_balance


class Grid:
    """docstring for Grid"""

    # BIMDATA - ajout de dip dans le __slot__
    __slots__ = ("cell_count", "cells_xyz", "cells_rgb", "cells_dip", "spacing")

    def __init__(self, node: Node, initial_count: int = 3) -> None:
        self.cell_count = np.array(
            [initial_count, initial_count, initial_count], dtype=np.int32
        )
        self.spacing = node.spacing * node.spacing

        # BIMDATA - ajout de cells_dip
        self.cells_xyz = List()
        self.cells_rgb = List()
        self.cells_dip = List()
        for _ in range(self.max_key_value):
            # BIMDATA - ajout de cells_dip
            self.cells_xyz.append(np.zeros((0, 3), dtype=np.float32))
            self.cells_rgb.append(np.zeros((0, 3), dtype=np.uint8))
            self.cells_dip.append(np.zeros((0, 3), dtype=np.uint8))

    def __getstate__(self) -> dict:
        # BIMDATA - ajout de cells_dip
        return {
            "cell_count": self.cell_count,
            "spacing": self.spacing,
            "cells_xyz": list(self.cells_xyz),
            "cells_rgb": list(self.cells_rgb),
            "cells_dip": list(self.cells_dip),
        }

    def __setstate__(self, state: dict):
        # BIMDATA - ajout de cells_dip
        self.cell_count = state["cell_count"]
        self.spacing = state["spacing"]
        self.cells_xyz = List(state["cells_xyz"])
        self.cells_rgb = List(state["cells_rgb"])
        self.cells_dip = List(state["cells_dip"])

    @property
    def max_key_value(self) -> int:
        return 1 << (
            2 * int(self.cell_count[0]).bit_length()
            + int(self.cell_count[2]).bit_length()
        )

    # BIMDATA - ajout de l'input dip
    def insert(
        self,
        aabmin: np.ndarray,
        inv_aabb_size: np.ndarray,
        xyz: np.ndarray,
        rgb: np.ndarray,
        dip: p.ndarray,
        force: bool = False,
    ) -> tuple[np.ndarray, np.ndarray, bool]:
        return _insert(
            self.cells_xyz,
            self.cells_rgb,
            # BIMDATA - ajout de cells_dip
            self.cells_dip,
            aabmin,
            inv_aabb_size,
            self.cell_count,
            xyz,
            rgb,
            # BIMDATA - ajout de dip
            dip,
            self.spacing,
            int(self.cell_count[0] - 1).bit_length(),
            force,
        )

    def needs_balance(self) -> bool:
        if self.cell_count[0] < 8:
            for cell in self.cells_xyz:
                if cell.shape[0] > 100000:
                    return True
        return False

    def balance(
        self, aabb_size: np.ndarray, aabmin: np.ndarray, inv_aabb_size: np.ndarray
    ) -> None:
        t = aabb_size_to_subdivision_type(aabb_size)
        self.cell_count[0] += 1
        self.cell_count[1] += 1
        # BIMDATA - ajout du dernier cell_count
        self.cell_count[2] += 1
        if t != SubdivisionType.QUADTREE:
            # BIMDATA - le cell count idx +1
            self.cell_count[3] += 1
        if self.cell_count[0] > 8:
            raise ValueError(
                f"The first value of the attribute cell count should be lower or equal to 8,"
                f"actual it is {self.cell_count[0]}"
            )

        old_cells_xyz = self.cells_xyz
        old_cells_rgb = self.cells_rgb
        # BIMDATA - ajout de old_cells_dip
        old_cells_dip = self.cells_dip
        self.cells_xyz = List()
        self.cells_rgb = List()
        # BIMDATA -- Ajout de cells_dip
        self.cells_dip = List()
        for _ in range(self.max_key_value):
            self.cells_xyz.append(np.zeros((0, 3), dtype=np.float32))
            self.cells_rgb.append(np.zeros((0, 3), dtype=np.uint8))
            # BIMDATA -- ajout de cells_dip
            self.cells_dip.append(np.zeros((0, 3), dtype=np.uint8))

        for cellxyz, cellrgb in zip(old_cells_xyz, old_cells_rgb):
            self.insert(aabmin, inv_aabb_size, cellxyz, cellrgb, True)

    def get_points(self, include_rgb: bool) -> np.ndarray:
        xyz = []
        rgb = []
        # BIMDATA -- ajout de dip
        dip = []
        pt = 0
        for i in range(len(self.cells_xyz)):
            xyz.append(self.cells_xyz[i].view(np.uint8).ravel())
            rgb.append(self.cells_rgb[i].ravel())
            # BIMDATA - ajout de cet append
            dip.append(self.cells_dip[i].ravel())
            pt += self.cells_xyz[i].shape[0]

        if include_rgb:
            # BIMDATA On concat égakement dip
            # Dans le cas d'une var avec rgb : pas nécéssairement ?
            res = np.concatenate(
                (np.concatenate(xyz), np.concatenate(rgb), np.concatenate(dip))
            )
            return res
        else:
            return np.concatenate(xyz)

    def get_point_count(self) -> int:
        pt = 0
        for i in range(len(self.cells_xyz)):
            pt += self.cells_xyz[i].shape[0]
        return pt
