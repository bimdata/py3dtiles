from abc import ABC


class SharedMetadata(ABC):
    """
    Base class with data that must be shared with worker tiler.
    Caution, the attributes must not be modified afterwards the creation since it is shared with several processes.
    """
