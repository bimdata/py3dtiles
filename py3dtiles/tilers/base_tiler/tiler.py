from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Generator, Generic, List, Optional, Tuple, TypeVar

from pyproj import CRS

from .shared_metadata import SharedMetadata
from .tiler_worker import TilerWorker

_SharedMetadataT = TypeVar("_SharedMetadataT", bound=SharedMetadata)
_TilerWorkerT = TypeVar("_TilerWorkerT", bound=TilerWorker[Any])


class Tiler(ABC, Generic[_SharedMetadataT, _TilerWorkerT]):
    """
    Tiler abstract class, this list of attributes and methods is used by convert.
    This class will organize the different tasks and their order of dispatch to the TilerWorker instances.

    You must set a name as class attribute and overwrite all abstract methods.

    Some methods are not required, overwrite them only if needed (like `validate_binary_data` or `memory_control`)
    """

    name = b""
    shared_metadata: _SharedMetadataT

    @abstractmethod
    def initialization(
        self,
        crs_out: Optional[CRS],
        working_dir: Path,
        number_of_jobs: int,
    ) -> None:
        """
        The __init__ method must only set attributes without any action.
        It is in this method that this work must be done (and the initialization of shared_metadata).

        The method will be called before all others.
        """

    @abstractmethod
    def get_worker(self) -> _TilerWorkerT:
        """
        Returns an instantiated tiler worker.
        """

    @abstractmethod
    def get_tasks(
        self, startup: float
    ) -> Generator[Tuple[bytes, List[bytes]], None, None]:
        """
        Returns a generator of tasks (command type and the content).

        The order of tasks should be prioritized. If there is no more idle process,
        the generator is stopped and will be recreated latter.
        """

    @abstractmethod
    def process_message(self, return_type: bytes, content: List[bytes]) -> bool:
        """
        Updates the state of the tiler in function of the return type and the returned data
        """

    @abstractmethod
    def write_tileset(self) -> None:
        """
        Writes the tileset file once the binary data written
        """

    def validate_binary_data(self) -> None:
        """
        Checks if the state of the tiler or the binary data written is correct.
        This method is called after the end of the conversion of this tiler (but before write_tileset)
        """

    def memory_control(self) -> None:
        """
        Method called at the end of each loop of the convert method.
        Checks if there is no too much memory used by the tiler and do actions in function
        """

    @abstractmethod
    def print_summary(self) -> None:
        """
        Prints the summary of the tiler before the start of the conversion.
        """

    def benchmark(self, benchmark_id: str, startup: float) -> None:
        """
        Prints benchmark info at the end of the conversion of this tiler and the writing of the tileset.
        """

    @abstractmethod
    def print_debug(
        self, now: float, number_of_jobs: int, number_of_idle_clients: int
    ) -> None:
        """
        Prints info about the progression of the conversion. Called everytime a tiler worker task is finished.
        """
