from abc import ABC, abstractmethod
from typing import Generic, List, TypeVar

import zmq

from py3dtiles.tilers.base_tiler.shared_metadata import SharedMetadata

_SharedMetadataT = TypeVar("_SharedMetadataT", bound=SharedMetadata)


class TilerWorker(ABC, Generic[_SharedMetadataT]):
    def __init__(self, shared_metadata: _SharedMetadataT):
        self.shared_metadata = shared_metadata

    @abstractmethod
    def execute(
        self, skt: zmq.Socket[bytes], command: bytes, content: List[bytes]
    ) -> None:
        ...
