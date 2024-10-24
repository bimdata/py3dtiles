from __future__ import annotations

import pickle
from collections.abc import Generator
from pathlib import Path
from typing import TYPE_CHECKING

import lz4.frame as gzip
import numpy as np
import numpy.typing as npt

import py3dtiles
from py3dtiles.tileset.content import Pnts
from py3dtiles.utils import node_name_to_path

if TYPE_CHECKING:
    from py3dtiles.tilers.point.node import DummyNode, Node


def points_to_pnts_file(
    name: bytes,
    points: npt.NDArray[np.uint8],
    out_folder: Path,
    include_rgb: bool,
    include_classification: bool,
    include_intensity: bool,
) -> tuple[int, Path]:
    """
    Write a pnts file from an uint8 data array containing:
     - points as SemanticPoint.POSITION
     - if include_rgb, rgb as SemanticPoint.RGB
     - if include_classification, classification as a single np.uint8 value
     - if include_intensity, intensity as a single np.uint8 value
    """
    pnts = Pnts.from_points(
        points, include_rgb, include_classification, include_intensity
    )

    node_path = node_name_to_path(out_folder, name, ".pnts")

    if node_path.exists():
        raise FileExistsError(f"{node_path} already written")

    pnts.save_as(node_path)

    return pnts.body.feature_table.nb_points(), node_path


def node_to_pnts(
    name: bytes,
    node: Node | DummyNode,
    out_folder: Path,
    include_rgb: bool,
    include_classification: bool,
    include_intensity: bool,
) -> int:
    points = py3dtiles.tilers.point.node.Node.get_points(
        node, include_rgb, include_classification, include_intensity
    )
    point_nb, _ = points_to_pnts_file(
        name, points, out_folder, include_rgb, include_classification, include_intensity
    )
    return point_nb


def run(
    data: bytes,
    folder: Path,
    write_rgb: bool,
    write_classification: bool,
    write_intensity: bool,
) -> Generator[int, None, None]:
    # we can safely write the .pnts file
    if len(data) > 0:
        root = pickle.loads(gzip.decompress(data))
        total = 0
        for name in root:
            node = py3dtiles.tilers.point.node.DummyNode(pickle.loads(root[name]))
            total += node_to_pnts(
                name, node, folder, write_rgb, write_classification, write_intensity
            )
        yield total
