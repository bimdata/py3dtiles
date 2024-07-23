from abc import ABC
from dataclasses import dataclass


@dataclass(frozen=True)
class SharedMetadata(ABC):
    """
    Base class with data that must be shared with worker tiler.
    """
