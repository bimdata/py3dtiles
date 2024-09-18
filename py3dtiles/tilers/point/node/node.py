from __future__ import annotations

import copy
import json
import pickle
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import TYPE_CHECKING, Any, Generator, Iterator, TypedDict

import numpy as np
import numpy.typing as npt

from py3dtiles.exceptions import TilerException
from py3dtiles.tilers.point.pnts import MIN_POINT_SIZE
from py3dtiles.tilers.point.pnts.pnts_writer import points_to_pnts_file
from py3dtiles.tileset.bounding_volume_box import BoundingVolumeBox
from py3dtiles.tileset.content import read_binary_tile_content
from py3dtiles.tileset.content.pnts_feature_table import SemanticPoint
from py3dtiles.tileset.tile import Tile
from py3dtiles.tileset.tileset import TileSet
from py3dtiles.utils import (
    SubdivisionType,
    aabb_size_to_subdivision_type,
    node_from_name,
    node_name_to_path,
)

from .distance import xyz_to_child_index
from .points_grid import Grid

if TYPE_CHECKING:
    from typing_extensions import NotRequired

    from .node_catalog import NodeCatalog


def node_to_tileset(
    args: tuple[Node, Path, npt.NDArray[np.float32], Node | None, int]
) -> Tile | None:
    return args[0].to_tileset(args[1], args[2], args[3], args[4], None)


class _DummyNodeDictType(TypedDict):
    children: NotRequired[list[bytes]]
    grid: NotRequired[Grid]
    points: NotRequired[
        list[
            tuple[
                npt.NDArray[np.float32],
                npt.NDArray[np.uint8],
                npt.NDArray[np.uint8],
                npt.NDArray[np.uint8],
            ]
        ]
    ]


class DummyNode:
    def __init__(self, _bytes: _DummyNodeDictType) -> None:
        if "children" in _bytes:
            self.children: list[bytes] | None = _bytes["children"]
            self.grid = _bytes["grid"]
        else:
            self.children = None
            self.points = _bytes["points"]


class Node:
    """docstring for Node"""

    __slots__ = (
        "name",
        "aabb",
        "aabb_size",
        "inv_aabb_size",
        "aabb_center",
        "spacing",
        "pending_xyz",
        "pending_rgb",
        "pending_classification",
        "pending_intensity",
        "children",
        "grid",
        "points",
        "dirty",
    )

    def __init__(
        self, name: bytes, aabb: npt.NDArray[np.float64 | np.float32], spacing: float
    ) -> None:
        super().__init__()
        self.name = name
        self.aabb = aabb.astype(
            np.float32
        )  # TODO remove astype once the whole typing is done (and once data type issues on numpy arrays are fixed).
        self.aabb_size = np.maximum(self.aabb[1] - self.aabb[0], MIN_POINT_SIZE)
        self.inv_aabb_size = 1.0 / self.aabb_size
        self.aabb_center = (self.aabb[0] + self.aabb[1]) * 0.5
        self.spacing = spacing
        self.pending_xyz: list[npt.NDArray[np.float32]] = []
        self.pending_rgb: list[npt.NDArray[np.uint8]] = []
        self.pending_classification: list[npt.NDArray[np.uint8]] = []
        self.pending_intensity: list[npt.NDArray[np.uint8]] = []
        self.children: list[bytes] | None = None
        self.grid = Grid(self)
        self.points: list[
            tuple[
                npt.NDArray[np.float32],
                npt.NDArray[np.uint8],
                npt.NDArray[np.uint8],
                npt.NDArray[np.uint8],
            ]
        ] = []
        self.dirty = False

    def save_to_bytes(self) -> bytes:
        sub_pickle: dict[str, Any] = {}
        if self.children is not None:
            sub_pickle["children"] = self.children
            sub_pickle["grid"] = self.grid
        else:
            sub_pickle["points"] = self.points

        return pickle.dumps(sub_pickle)

    def load_from_bytes(self, byt: bytes) -> None:
        sub_pickle = pickle.loads(byt)
        if "children" in sub_pickle:
            self.children = sub_pickle["children"]
            self.grid = sub_pickle["grid"]
        else:
            self.points = sub_pickle["points"]

    def insert(
        self,
        scale: float,
        xyz: npt.NDArray[np.float32],
        rgb: npt.NDArray[np.uint8],
        classification: npt.NDArray[np.uint8],
        intensity: npt.NDArray[np.uint8],
        make_empty_node: bool = False,
    ) -> None:
        if make_empty_node:
            self.children = []
            self.pending_xyz += [xyz]
            self.pending_rgb += [rgb]
            self.pending_classification += [classification]
            self.pending_intensity += [intensity]
            return

        # fastpath
        if self.children is None:
            self.points.append((xyz, rgb, classification, intensity))
            count = sum([xyz.shape[0] for xyz, _, _, _ in self.points])
            # stop subdividing if spacing is 1mm
            if count >= 20000 and self.spacing > 0.001 * scale:
                self._split(scale)
            self.dirty = True

            return

        # grid based insertion
        (
            remainder_xyz,
            remainder_rgb,
            remainder_classification,
            remainder_intensity,
            needs_balance,
        ) = self.grid.insert(
            self.aabb[0], self.inv_aabb_size, xyz, rgb, classification, intensity
        )

        if needs_balance:
            self.grid.balance(self.aabb_size, self.aabb[0], self.inv_aabb_size)
            self.dirty = True

        self.dirty = self.dirty or (len(remainder_xyz) != len(xyz))

        if len(remainder_xyz) > 0:
            self.pending_xyz += [remainder_xyz]
            self.pending_rgb += [remainder_rgb]
            self.pending_classification += [remainder_classification]
            self.pending_intensity += [remainder_intensity]

    def needs_balance(self) -> bool:
        if self.children is not None:
            return self.grid.needs_balance()
        return False

    def flush_pending_points(self, catalog: NodeCatalog, scale: float) -> None:
        for name, xyz, rgb, classification, intensity in self._get_pending_points():
            catalog.get_node(name).insert(scale, xyz, rgb, classification, intensity)
        self.pending_xyz = []
        self.pending_rgb = []
        self.pending_classification = []
        self.pending_intensity = []

    def dump_pending_points(self) -> list[tuple[bytes, bytes, int]]:
        result = [
            (
                name,
                pickle.dumps(
                    {
                        "xyz": xyz,
                        "rgb": rgb,
                        "classification": classification,
                        "intensity": intensity,
                    }
                ),
                len(xyz),
            )
            for name, xyz, rgb, classification, intensity in self._get_pending_points()
        ]

        self.pending_xyz = []
        self.pending_rgb = []
        self.pending_classification = []
        self.pending_intensity = []
        return result

    def get_pending_points_count(self) -> int:
        return sum([xyz.shape[0] for xyz in self.pending_xyz])

    def _get_pending_points(
        self,
    ) -> Iterator[
        tuple[
            bytes,
            npt.NDArray[np.float32],
            npt.NDArray[np.uint8],
            npt.NDArray[np.uint8],
            npt.NDArray[np.uint8],
        ]
    ]:
        if not self.pending_xyz:
            return

        pending_xyz_arr = np.concatenate(self.pending_xyz)
        pending_rgb_arr = np.concatenate(self.pending_rgb)
        pending_classification_arr = np.concatenate(self.pending_classification)
        pending_intensity_arr = np.concatenate(self.pending_intensity)
        t = aabb_size_to_subdivision_type(self.aabb_size)
        if t == SubdivisionType.QUADTREE:
            indices = xyz_to_child_index(
                pending_xyz_arr,
                np.array(
                    [self.aabb_center[0], self.aabb_center[1], self.aabb[1][2]],
                    dtype=np.float32,
                ),
            )
        else:
            indices = xyz_to_child_index(pending_xyz_arr, self.aabb_center)

        # unique children list
        childs = np.unique(indices)

        # make sure all children nodes exist
        for child in childs:
            name = "{}{}".format(self.name.decode("ascii"), child).encode("ascii")
            # create missing nodes, only for remembering they exist.
            # We don't want to serialize them
            # probably not needed...
            if self.children is not None and name not in self.children:
                self.children += [name]
                self.dirty = True
                # print('Added node {}'.format(name))

            mask = np.where(indices - child == 0)
            xyz = pending_xyz_arr[mask]
            if len(xyz) > 0:
                yield name, xyz, pending_rgb_arr[mask], pending_classification_arr[
                    mask
                ], pending_intensity_arr[mask]

    def _split(self, scale: float) -> None:
        self.children = []
        for xyz, rgb, classification, intensity in self.points:
            self.insert(scale, xyz, rgb, classification, intensity)
        self.points = []

    def get_point_count(
        self, node_catalog: NodeCatalog, max_depth: int, depth: int = 0
    ) -> int:
        if self.children is None:
            return sum([xyz.shape[0] for xyz, _, _, _ in self.points])
        else:
            count = self.grid.get_point_count()
            if depth < max_depth:
                for n in self.children:
                    count += node_catalog.get_node(n).get_point_count(
                        node_catalog, max_depth, depth + 1
                    )
            return count

    @staticmethod
    def get_points(
        data: Node | DummyNode,
        include_rgb: bool,
        include_classification: bool,
        include_intensity: bool,
    ) -> npt.NDArray[np.uint8]:  # todo remove staticmethod
        if data.children is None:
            points = data.points
            xyz = (
                np.concatenate(tuple([xyz for xyz, _, _, _ in points]))
                .view(np.uint8)
                .ravel()
            )

            if include_rgb:
                rgb = np.concatenate(tuple([rgb for _, rgb, _, _ in points])).ravel()
            else:
                rgb = np.array([], dtype=np.uint8)

            if include_classification:
                classification = np.concatenate(
                    tuple([classification for _, _, classification, _ in points])
                ).ravel()
            else:
                classification = np.array([], dtype=np.uint8)

            if include_intensity:
                intensity = np.concatenate(
                    tuple([intensity for _, _, _, intensity in points])
                ).ravel()
            else:
                intensity = np.array([], dtype=np.uint8)

            return np.concatenate((xyz, rgb, classification, intensity))
        else:
            return data.grid.get_points(
                include_rgb, include_classification, include_intensity
            )

    def get_child_names(self) -> Generator[bytes, None, None]:
        for number_child in range(8):
            yield f"{self.name.decode('ascii')}{number_child}".encode("ascii")

    def to_tileset(
        self,
        folder: Path,
        scale: npt.NDArray[np.float32],
        parent_node: Node | None = None,
        depth: int = 0,
        pool_executor: ProcessPoolExecutor | None = None,
    ) -> Tile | None:
        # create child tileset parts
        # if their size is below of 100 points, they will be merged in this node.
        children_tileset_parts: list[Tile] = []
        parameter_to_compute: list[
            tuple[Node, Path, npt.NDArray[np.float32], Node, int]
        ] = []
        for child_name in self.get_child_names():
            child_node = node_from_name(child_name, self.aabb, self.spacing)
            child_pnts_path = node_name_to_path(folder, child_name, ".pnts")

            if child_pnts_path.exists():
                # multi thread is only allowed on nodes where there are no prune
                # a simple rule is: only is there is not a parent node
                if pool_executor and parent_node is None:
                    parameter_to_compute.append(
                        (child_node, folder, scale, self, depth + 1)
                    )
                else:
                    children_tileset_part = child_node.to_tileset(
                        folder, scale, self, depth + 1
                    )
                    if (
                        children_tileset_part is not None
                    ):  # return None if the child has been merged
                        children_tileset_parts.append(children_tileset_part)

        if pool_executor and parent_node is None:
            children_tileset_parts = [
                t
                for t in pool_executor.map(node_to_tileset, parameter_to_compute)
                if t is not None
            ]

        pnts_path = node_name_to_path(folder, self.name, ".pnts")
        tile_content = read_binary_tile_content(pnts_path)
        fth = tile_content.body.feature_table.header
        xyz = tile_content.body.feature_table.body.position

        # check if this node should be merged in the parent.
        prune = False  # prune only if the node is a leaf

        # If this child is small enough, merge in the current tile
        if parent_node is not None and depth > 1 and fth.points_length < 100:
            parent_pnts_path = node_name_to_path(folder, parent_node.name, ".pnts")
            parent_tile = read_binary_tile_content(parent_pnts_path)
            parent_fth = parent_tile.body.feature_table.header

            parent_xyz = parent_tile.body.feature_table.body.position

            if (
                parent_fth.colors != SemanticPoint.NONE
                and parent_tile.body.feature_table.body.color is not None
            ):
                parent_rgb = parent_tile.body.feature_table.body.color
            else:
                parent_rgb = np.array([], dtype=np.uint8)

            if "Classification" in parent_tile.body.batch_table.header.data:
                parent_classification = (
                    parent_tile.body.batch_table.get_binary_property("Classification")
                )
            else:
                parent_classification = np.array([], dtype=np.uint8)

            if "Intensity" in parent_tile.body.batch_table.header.data:
                parent_intensity = parent_tile.body.batch_table.get_binary_property(
                    "Intensity"
                )
            else:
                parent_intensity = np.array([], dtype=np.uint8)

            parent_xyz_float = parent_xyz.reshape((parent_fth.points_length, 3))
            # update aabb based on real values
            parent_bounding_volume = BoundingVolumeBox.from_points(parent_xyz_float)

            parent_xyz = np.concatenate((parent_xyz, xyz))

            if fth.colors != SemanticPoint.NONE:
                if tile_content.body.feature_table.body.color is None:
                    raise TilerException(
                        "If the parent has color data, the children must also have color data."
                    )
                parent_rgb = np.concatenate(
                    (parent_rgb, tile_content.body.feature_table.body.color)
                )

            if "Classification" in tile_content.body.batch_table.header.data:
                parent_classification = np.concatenate(
                    (
                        parent_classification,
                        tile_content.body.batch_table.get_binary_property(
                            "Classification"
                        ),
                    )
                )

            if "Intensity" in tile_content.body.batch_table.header.data:
                parent_intensity = np.concatenate(
                    (
                        parent_intensity,
                        tile_content.body.batch_table.get_binary_property("Intensity"),
                    )
                )

            # update aabb
            xyz_float = xyz.view(np.float32).reshape((fth.points_length, 3))
            new_bounding_volume_box = BoundingVolumeBox.from_points(xyz_float)

            parent_bounding_volume.add(new_bounding_volume_box)

            parent_pnts_path.unlink()
            points_to_pnts_file(
                parent_node.name,
                np.concatenate(
                    (
                        parent_xyz.view(np.uint8),
                        parent_rgb,
                        parent_classification,
                        parent_intensity,
                    )
                ),
                folder,
                len(parent_rgb) != 0,
                len(parent_classification) != 0,
                len(parent_intensity) != 0,
            )
            pnts_path.unlink()
            prune = True

        content_uri = None
        if not prune:
            content_uri = pnts_path.relative_to(folder)
            xyz_float = xyz.view(np.float32).reshape((fth.points_length, 3))

            # update aabb based on real values
            bounding_box = BoundingVolumeBox.from_points(xyz_float)

        else:
            # if it is a leaf that should be pruned
            if not children_tileset_parts:
                return None

            # recompute the aabb in function of children
            bounding_box = BoundingVolumeBox()
            for child_tileset_part in children_tileset_parts:
                if child_tileset_part.bounding_volume is not None:
                    bounding_box.add(child_tileset_part.bounding_volume)

        if bounding_box is None:
            raise TilerException("bounding_box shouldn't be None")

        tile: Tile = Tile(
            geometric_error=10 * self.spacing / scale[0], bounding_volume=bounding_box
        )
        if content_uri is not None:
            tile.content_uri = content_uri

        if children_tileset_parts:
            tile.children = children_tileset_parts
        else:
            tile.geometric_error = 0.0

        if (
            len(self.name) > 0
            and children_tileset_parts
            and len(json.dumps(tile.to_dict())) > 100000
        ):
            tile = split_tileset(tile, self.name.decode(), folder)

        return tile


def split_tileset(tile: Tile, split_name: str, folder: Path) -> Tile:
    tile.set_refine_mode("ADD")
    tileset = TileSet(geometric_error=tile.geometric_error)
    tileset.root_tile = copy.deepcopy(tile)
    tileset_name = Path(f"tileset.{split_name}.json")
    tileset.write_as_json(folder / tileset_name)
    tile.content_uri = tileset_name
    tile.children = []

    return tile
