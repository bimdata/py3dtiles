from __future__ import annotations

import shutil
from enum import Enum
from io import StringIO
from pathlib import Path, PurePath
from typing import TYPE_CHECKING, Callable, TypeVar

import numpy as np
import numpy.typing as npt
from pyproj import CRS

from py3dtiles.reader import xyz_reader

if TYPE_CHECKING:
    from typing_extensions import ParamSpec

    from py3dtiles.tilers.point.node import Node

_T = TypeVar("_T", bound=npt.NBitBase)

MIN_AABB_SIZE = 0.00001


def str_to_CRS(srs: str | CRS | None) -> CRS | None:
    """
    Convert a string in a pyproj CRS object. The string could be an epsg code or a Proj4 string. If srs is already
    a CRS object, the function returns the same CRS definition.
    """
    if srs is None:
        return None

    try:
        return CRS.from_epsg(int(srs))  # type: ignore [arg-type]
    except ValueError:
        return CRS(srs)


READER_MAP = {
    ".xyz": xyz_reader,
    ".csv": xyz_reader,
}

try:
    from py3dtiles.reader import las_reader

    READER_MAP[".las"] = las_reader
    # then check for the presence of laz support
    from importlib.util import find_spec

    if find_spec("laszip") or find_spec("lazrs"):
        READER_MAP[".laz"] = las_reader
except ImportError:
    pass

try:
    from py3dtiles.reader import ply_reader

    READER_MAP[".ply"] = ply_reader
except ImportError:
    pass


if TYPE_CHECKING:
    Param = ParamSpec("Param")
    RetType = TypeVar("RetType")


def profile(func: Callable[Param, RetType]) -> Callable[Param, RetType]:
    from line_profiler import LineProfiler

    def wrapper(*args, **kwargs):  # type: ignore [no-untyped-def]
        lp = LineProfiler()
        deco = lp(func)
        res = deco(*args, **kwargs)
        s = StringIO()
        lp.print_stats(stream=s)
        print(s.getvalue())
        return res

    return wrapper


class SubdivisionType(Enum):
    OCTREE = 1
    QUADTREE = 2


def node_name_to_path(
    working_dir: Path, name: bytes, suffix: str = "", split_len: int = 8
) -> Path:
    """
    Get the path of a tile from its name and the working directory.
    If the name is '222262175' with the suffix '.pnts', the result is 'working_dir/22226217/r5.pnts'
    """
    str_name = name.decode("ascii")
    if len(str_name) <= split_len:
        filename = PurePath("r" + str_name + suffix)
    else:
        # the name is split on every 'split_len' char to avoid to have too many tiles on the same folder.
        sub_folders = [
            str_name[i : i + split_len] for i in range(0, len(str_name), split_len)
        ]
        working_dir = working_dir.joinpath(*sub_folders[:-1])
        filename = PurePath("r" + sub_folders[-1] + suffix)

    full_path = working_dir / filename
    working_dir.mkdir(parents=True, exist_ok=True)

    return full_path


def compute_spacing(aabb: npt.NDArray[np.floating[_T]]) -> float:
    return float(np.linalg.norm(aabb[1] - aabb[0]) / 125)


def aabb_size_to_subdivision_type(
    size: npt.NDArray[np.floating[_T]],
) -> SubdivisionType:
    if size[2] / min(size[0], size[1]) < 0.5:
        return SubdivisionType.QUADTREE
    else:
        return SubdivisionType.OCTREE


def split_aabb(
    aabb: npt.NDArray[np.floating[_T]], index: int, force_quadtree: bool = False
) -> npt.NDArray[np.floating[_T]]:
    half = (aabb[1] - aabb[0]) * 0.5
    t = aabb_size_to_subdivision_type(half)

    new_aabb = np.array([aabb[0], aabb[0] + half])
    if index & 4:
        new_aabb[0][0] += half[0]
        new_aabb[1][0] += half[0]
    if index & 2:
        new_aabb[0][1] += half[1]
        new_aabb[1][1] += half[1]

    if force_quadtree or t == SubdivisionType.QUADTREE:
        new_aabb[1][2] += half[2]
    elif index & 1:
        new_aabb[0][2] += half[2]
        new_aabb[1][2] += half[2]

    return new_aabb


def make_aabb_cubic(aabb: npt.NDArray[np.floating[_T]]) -> npt.NDArray[np.floating[_T]]:
    s = max(aabb[1] - aabb[0])
    aabb[1][0] = aabb[0][0] + s
    aabb[1][1] = aabb[0][1] + s
    aabb[1][2] = aabb[0][2] + s
    return aabb


def make_aabb_valid(aabb: npt.NDArray[np.float64]) -> None:
    """
    Modify inplace the aabb so that no dimension is 0-sized
    """
    for i in range(3):
        if aabb[0][i] == aabb[1][i]:
            aabb[1][i] = aabb[1][i] + MIN_AABB_SIZE


def node_from_name(
    name: bytes,
    parent_aabb: npt.NDArray[np.floating[_T]],
    parent_spacing: float,
) -> Node:
    from py3dtiles.tilers.point.node import Node

    spacing = parent_spacing * 0.5
    aabb = split_aabb(parent_aabb, int(name[-1])) if len(name) > 0 else parent_aabb
    # let's build a new Node
    return Node(name, aabb.astype(np.float64), spacing)


def mkdir_or_raise(folder: Path, overwrite: bool = False) -> None:
    """
    Create a folder if it can (it doesn't exist or is empty).

    If folder is a file or is not empty, raise a `FileExistsError`.

    If overwrite is True, delete a possibly existing folder. Never delete anything if it is not a folder.

    :param folder: Path object representing the needed folder
    :param overwrite: Whether this method can brutally remove existing non-empty folder. **Warning** this is ***destructive*** and the equivalent of `rm -rf folder`, you have been warn.
    :raises FileExistsError: when `folder` is actually a file or a non-empty folder.
    """
    if folder.exists():
        if folder.is_dir():
            if overwrite:
                shutil.rmtree(folder, ignore_errors=True)
                folder.mkdir()
            else:
                # check that folder is empty
                it = folder.iterdir()
                if any(it):
                    raise FileExistsError(
                        f"Folder '{folder}' already exists and is not empty."
                    )
        else:
            raise FileExistsError(
                f"'{folder}' already exists and is not a directory. Not deleting it."
            )
    else:
        folder.mkdir()
