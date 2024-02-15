"""
This module contains supporting classes and functions to manipulate 3DTiles data structure.

Use this module if you plan on directly reading, manipulating and writing tilesets, tiles and tile contents.
"""
from .bounding_volume import BoundingVolume
from .bounding_volume_box import BoundingVolumeBox
from .root_property import RootProperty
from .tile import Tile
from .tileset import TileSet
from .utils import number_of_points_in_tileset

__all__ = [
    "BoundingVolume",
    "BoundingVolumeBox",
    "content",
    "extension",
    "number_of_points_in_tileset",
    "RootProperty",
    "Tile",
    "TileSet",
]
