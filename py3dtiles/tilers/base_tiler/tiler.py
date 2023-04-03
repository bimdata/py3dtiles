from abc import abstractmethod
from pathlib import Path
from typing import Any, Generator, Generic, List, Optional, Tuple, TypeVar

from pyproj import CRS

from .shared_metadata import SharedMetadata
from .tiler_worker import TilerWorker

_SharedMetadataT = TypeVar("_SharedMetadataT", bound=SharedMetadata)
_TilerWorkerT = TypeVar("_TilerWorkerT", bound=TilerWorker[Any])


class Tiler(Generic[_SharedMetadataT, _TilerWorkerT]):
    name = b""
    shared_metadata: _SharedMetadataT

    @abstractmethod
    def initialization(
        self,
        crs_out: Optional[CRS],
        working_dir: Path,
        number_of_jobs: int,
    ) -> None:
        ...

    @abstractmethod
    def get_worker(self) -> _TilerWorkerT:
        ...

    @abstractmethod
    def get_tasks(
        self, startup: float
    ) -> Generator[Tuple[bytes, List[bytes]], None, None]:
        ...

    @abstractmethod
    def process_message(self, return_type: bytes, content: List[bytes]) -> bool:
        ...

    @abstractmethod
    def print_summary(self) -> None:
        ...

    @abstractmethod
    def write_tileset(self) -> None:
        ...

    def validate_binary_data(self) -> None:
        pass

    def memory_control(self) -> None:
        pass

    def benchmark(self, benchmark_id: str, startup: float) -> None:
        pass

    @abstractmethod
    def print_debug(
        self, now: float, number_of_jobs: int, number_of_idle_clients: int
    ) -> None:
        ...
