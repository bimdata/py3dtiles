import argparse
import os
import pickle
import shutil
import sys
import tempfile
import time
import traceback
from multiprocessing import Process, cpu_count
from pathlib import Path
from time import sleep
from typing import Any, Dict, List, Optional, Set, Union

import psutil
import zmq
from pyproj import CRS

from py3dtiles.constants import EXIT_CODES
from py3dtiles.exceptions import (
    Py3dtilesException,
    SrsInMissingException,
    TilerException,
    WorkerException,
)
from py3dtiles.tilers.base_tiler import Tiler
from py3dtiles.tilers.base_tiler.message_type import ManagerMessage, WorkerMessageType
from py3dtiles.tilers.base_tiler.tiler_worker import TilerWorker
from py3dtiles.tilers.point.point_tiler import PointTiler
from py3dtiles.utils import mkdir_or_raise, str_to_CRS

TOTAL_MEMORY_MB = int(psutil.virtual_memory().total / (1024 * 1024))
DEFAULT_CACHE_SIZE = int(TOTAL_MEMORY_MB / 10)
CPU_COUNT = cpu_count()

# IPC protocol is not supported on Windows
if os.name == "nt":
    URI = "tcp://127.0.0.1:0"
else:
    # Generate a unique name for this socket
    tmpdir = tempfile.TemporaryDirectory()
    URI = f"ipc://{tmpdir.name}/py3dtiles.sock"


META_TILER_NAME = b"meta"


def _worker_target(
    worker_tilers: Dict[bytes, TilerWorker[Any]],
    verbosity: int,
    uri: bytes,
) -> None:
    return _WorkerDispatcher(
        worker_tilers,
        verbosity,
        uri,
    ).run()


class _WorkerDispatcher:
    """
    This class waits from jobs commands from the Zmq socket.
    """

    skt: zmq.Socket[bytes]

    def __init__(
        self,
        worker_tilers: Dict[bytes, TilerWorker[Any]],
        verbosity: int,
        uri: bytes,
    ) -> None:
        self.worker_tilers = worker_tilers
        self.verbosity = verbosity
        self.uri = uri

        # Socket to receive messages on
        self.context = zmq.Context()

    def run(self) -> None:
        self.skt = self.context.socket(zmq.DEALER)

        self.skt.connect(self.uri)  # type: ignore [arg-type]

        startup_time = time.time()
        idle_time = 0.0

        # notify we're ready
        self.skt.send_multipart([WorkerMessageType.REGISTER.value])

        while True:
            try:
                before = time.time() - startup_time
                self.skt.poll()
                after = time.time() - startup_time

                idle_time += after - before

                message = self.skt.recv_multipart()
                tiler_name = message[1]
                command = message[2]
                content = message[3:]

                delta = time.time() - pickle.loads(message[0])
                if delta > 0.01 and self.verbosity >= 1:
                    print(
                        f"{os.getpid()} / {round(after, 2)} : Delta time: {round(delta, 3)}"
                    )

                if command == ManagerMessage.SHUTDOWN.value:
                    break  # ack
                else:
                    self.worker_tilers[tiler_name].execute(self.skt, command, content)

                # notify we're idle
                self.skt.send_multipart([WorkerMessageType.IDLE.value])
            except Exception as e:
                traceback.print_exc()
                error_message = f"{e.__class__.__module__}.{e.__class__.__name__}: {e}"
                self.skt.send_multipart(
                    [WorkerMessageType.ERROR.value, error_message.encode()]
                )
                # we still print it for stacktraces

        if self.verbosity >= 1:
            print(
                "total: {} sec, idle: {}".format(
                    round(time.time() - startup_time, 1), round(idle_time, 1)
                )
            )

        self.skt.send_multipart([WorkerMessageType.HALTED.value])


# Manager
class _ZmqManager:
    """
    This class sends messages to the workers.
    We can also request general status.
    """

    def __init__(
        self,
        number_of_jobs: int,
        worker_tilers: Dict[bytes, TilerWorker[Any]],
        verbosity: int,
    ) -> None:
        """
        For the process_args argument, see the init method of Worker
        to get the list of needed parameters.
        """
        self.context = zmq.Context()

        self.number_of_jobs = number_of_jobs

        self.socket = self.context.socket(zmq.ROUTER)
        self.socket.bind(URI)
        # Useful only when TCP is used to get the URI with the opened port
        self.uri = self.socket.getsockopt(zmq.LAST_ENDPOINT)
        if not isinstance(self.uri, bytes):
            raise RuntimeError(
                "The uri returned by self.socket.getsockopt should be bytes."
            )

        self.processes = [
            Process(
                target=_worker_target,
                args=(worker_tilers, verbosity, self.uri),
            )
            for _ in range(number_of_jobs)
        ]
        for p in self.processes:
            p.start()

        self.activities = [p.pid for p in self.processes]
        self.clients: Set[bytes] = set()
        self.idle_clients: Set[bytes] = set()

        self.killing_processes = False
        self.number_processes_killed = 0
        self.time_waiting_an_idle_process = 0.0

    def all_clients_registered(self) -> bool:
        return len(self.clients) == self.number_of_jobs

    def send_to_process(self, message: List[bytes]) -> None:
        if not self.idle_clients:
            raise ValueError("idle_clients is empty")
        self.socket.send_multipart(
            [self.idle_clients.pop(), pickle.dumps(time.time())] + message
        )

    def send_to_all_processes(self, message: List[bytes]) -> None:
        if len(self.clients) == 0:
            raise ValueError("No registered clients")
        for client in self.clients:
            self.socket.send_multipart([client, pickle.dumps(time.time())] + message)

    def send_to_all_idle_processes(self, message: List[bytes]) -> None:
        if not self.idle_clients:
            raise ValueError("idle_clients is empty")
        for client in self.idle_clients:
            self.socket.send_multipart([client, pickle.dumps(time.time())] + message)
        self.idle_clients.clear()

    def can_queue_more_jobs(self) -> bool:
        return len(self.idle_clients) != 0

    def register_client(self, client_id: bytes) -> None:
        if client_id in self.clients:
            print(f"Warning: {client_id!r} already registered")
        else:
            self.clients.add(client_id)
        self.add_idle_client(client_id)

    def add_idle_client(self, client_id: bytes) -> None:
        if client_id in self.idle_clients:
            raise ValueError(f"The client id {client_id!r} is already in idle_clients")
        self.idle_clients.add(client_id)

    def are_all_processes_idle(self) -> bool:
        return len(self.idle_clients) == self.number_of_jobs

    def are_all_processes_killed(self) -> bool:
        return self.number_processes_killed == self.number_of_jobs

    def shutdown_all_processes(self) -> None:
        self.send_to_all_processes([META_TILER_NAME, ManagerMessage.SHUTDOWN.value])
        self.killing_processes = True

    def join_all_processes(self) -> None:
        for p in self.processes:
            p.join()


def convert(
    files: Union[List[Union[str, Path]], str, Path],
    outfolder: Union[str, Path] = "./3dtiles",
    overwrite: bool = False,
    jobs: int = CPU_COUNT,
    cache_size: int = DEFAULT_CACHE_SIZE,
    crs_out: Optional[CRS] = None,
    crs_in: Optional[CRS] = None,
    force_crs_in: bool = False,
    benchmark: Optional[str] = None,
    rgb: bool = True,
    classification: bool = True,
    intensity: bool = True,
    color_scale: Optional[float] = None,
    verbose: int = False,
) -> None:
    """
    Convert the input dataset into 3dtiles. For the argument list and their effects, please see :py:class:`.Converter`.

    :param files: Filenames to process. The file must use the .las, .laz, .xyz or .ply format.
    :param outfolder: The folder where the resulting tileset will be written.
    :param overwrite: Overwrite the ouput folder if it already exists.
    :param jobs: The number of parallel jobs to start. Default to the number of cpu.
    :param cache_size: Cache size in MB. Default to available memory / 10.
    :param crs_out: CRS to convert the output with
    :param crs_in: Set a default input CRS
    :param force_crs_in: Force every input CRS to be `crs_in`, even if not null
    :param benchmark: Print summary at the end of the process
    :param rgb: Export rgb attributes.
    :param classification: Export classification attribute.
    :param intensity: Export intensity attributes. This support is currently limited to unsigned 8 bits integer for ply files, and to integers for xyz files.
    :param color_scale: Scale the color with the specified amount. Useful to lighten or darken black pointclouds with only intensity.

    :raises SrsInMissingException: if py3dtiles couldn't find srs informations in input files and srs_in is not specified
    :raises SrsInMixinException: if the input files have different CRS

    """
    converter = _Convert(
        files,
        outfolder=outfolder,
        overwrite=overwrite,
        jobs=jobs,
        cache_size=cache_size,
        crs_out=crs_out,
        crs_in=crs_in,
        force_crs_in=force_crs_in,
        benchmark=benchmark,
        rgb=rgb,
        classification=classification,
        intensity=intensity,
        color_scale=color_scale,
        verbose=verbose,
    )
    return converter.convert()


class _Convert:
    def __init__(
        self,
        files: Union[List[Union[str, Path]], str, Path],
        outfolder: Union[str, Path] = "./3dtiles",
        overwrite: bool = False,
        jobs: int = CPU_COUNT,
        cache_size: int = DEFAULT_CACHE_SIZE,
        crs_out: Optional[CRS] = None,
        crs_in: Optional[CRS] = None,
        force_crs_in: bool = False,
        benchmark: Optional[str] = None,
        rgb: bool = True,
        classification: bool = True,
        intensity: bool = True,
        color_scale: Optional[float] = None,
        verbose: int = False,
    ) -> None:
        """
        :param files: Filenames to process. The file must use the .las, .laz, .xyz or .ply format.
        :param outfolder: The folder where the resulting tileset will be written.
        :param overwrite: Overwrite the ouput folder if it already exists.
        :param jobs: The number of parallel jobs to start. Default to the number of cpu.
        :param cache_size: Cache size in MB. Default to available memory / 10.
        :param crs_out: CRS to convert the output with
        :param crs_in: Set a default input CRS
        :param force_crs_in: Force every input CRS to be `crs_in`, even if not null
        :param benchmark: Print summary at the end of the process
        :param rgb: Export rgb attributes.
        :param classification: Export classification attribute.
        :param intensity: Export intensity attribute.
        :param color_scale: Scale the color with the specified amount. Useful to lighten or darken black pointclouds with only intensity.

        :raises SrsInMissingException: if py3dtiles couldn't find srs informations in input files and srs_in is not specified
        :raises SrsInMixinException: if the input files have different CRS

        """
        # create folder
        self.out_folder = Path(outfolder)
        mkdir_or_raise(self.out_folder, overwrite=overwrite)

        self.tilers = [
            PointTiler(
                self.out_folder,
                files,
                crs_in,
                force_crs_in,
                rgb,
                classification,
                intensity,
                color_scale,
                cache_size,
                verbose,
            )
        ]

        self.jobs = jobs

        self.verbose = verbose
        self.benchmark = benchmark

        self.working_dir = self.out_folder / "tmp"
        self.working_dir.mkdir(parents=True)

        worker_tilers: Dict[bytes, TilerWorker[Any]] = {}
        for tiler in self.tilers:
            if tiler.name in worker_tilers:
                raise TilerException("There are tilers with the same attribute name.")

            try:
                tiler.initialization(
                    crs_out, self.working_dir / str(tiler.name), self.jobs
                )
            except Py3dtilesException as e:
                shutil.rmtree(self.out_folder)
                raise e

            worker_tilers[tiler.name] = tiler.get_worker()

        if self.verbose >= 1:
            for tiler in self.tilers:
                tiler.print_summary()

        self.zmq_manager = _ZmqManager(
            self.jobs,
            worker_tilers,
            self.verbose,
        )

    def convert(self) -> None:
        """convert

        Convert pointclouds (xyz, las or laz) to 3dtiles tileset containing pnts node
        """
        startup: float = time.time()

        try:
            for tiler in self.tilers:
                while True:
                    now = time.time() - startup

                    at_least_one_job_ended = False
                    if (
                        not self.zmq_manager.can_queue_more_jobs()
                        or self.zmq_manager.socket.poll(timeout=0, flags=zmq.POLLIN)
                    ):
                        at_least_one_job_ended = self.process_message(tiler)

                    # we wait for all processes/threads to register
                    # if we don't there are tricky cases where an exception fires in a worker before all the workers registered, which means that not all workers will receive the shutdown signal
                    if not self.zmq_manager.all_clients_registered():
                        sleep(0.1)
                        continue

                    if self.zmq_manager.can_queue_more_jobs():
                        for command, data in tiler.get_tasks(startup):
                            self.zmq_manager.send_to_process(
                                [PointTiler.name, command] + data
                            )
                            if not self.zmq_manager.can_queue_more_jobs():
                                break

                    # if at this point we have no work in progress => we're done
                    if self.zmq_manager.are_all_processes_idle():
                        break

                    if at_least_one_job_ended:
                        tiler.print_debug(
                            now, self.jobs, len(self.zmq_manager.idle_clients)
                        )

                    tiler.memory_control()

                tiler.validate_binary_data()

                if self.verbose >= 1:
                    print("Writing 3dtiles")

                tiler.write_tileset()
                shutil.rmtree(self.working_dir / str(tiler.name), ignore_errors=True)

                if self.verbose >= 1:
                    print(f"Tiler {tiler.name!r} done")

                if self.benchmark:
                    tiler.benchmark(self.benchmark, startup)

        finally:
            self.zmq_manager.shutdown_all_processes()
            self.zmq_manager.join_all_processes()

            if self.verbose >= 1:
                print(
                    "destroy", round(self.zmq_manager.time_waiting_an_idle_process, 2)
                )

            self.zmq_manager.context.destroy()

    def process_message(self, tiler: Tiler[Any, Any]) -> bool:
        at_least_one_job_ended = False

        # Blocking read but it's fine because either all our child processes are busy
        # or we know that there's something to read (zmq.POLLIN)
        start = time.time()
        message = self.zmq_manager.socket.recv_multipart()

        client_id = message[0]
        return_type = message[1]
        content = message[2:]

        if return_type == WorkerMessageType.REGISTER.value:
            self.zmq_manager.register_client(client_id)
        elif return_type == WorkerMessageType.IDLE.value:
            self.zmq_manager.add_idle_client(client_id)

            if not self.zmq_manager.can_queue_more_jobs():
                self.zmq_manager.time_waiting_an_idle_process += time.time() - start

        elif return_type == WorkerMessageType.HALTED.value:
            self.zmq_manager.number_processes_killed += 1

        elif return_type == WorkerMessageType.ERROR.value:
            raise WorkerException(
                f"An exception occurred in a worker: {content[0].decode()}"
            )

        else:
            at_least_one_job_ended = tiler.process_message(return_type, content)

        return at_least_one_job_ended


def _init_parser(
    subparser: "argparse._SubParsersAction[Any]",
) -> argparse.ArgumentParser:
    parser: argparse.ArgumentParser = subparser.add_parser(
        "convert",
        help="Convert input 3D data to a 3dtiles tileset.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "files",
        nargs="+",
        help="Filenames to process. The file must use the .las, .laz (lastools must be installed), .xyz or .ply format.",
    )
    parser.add_argument(
        "--out",
        type=str,
        help="The folder where the resulting tileset will be written.",
        default="./3dtiles",
    )
    parser.add_argument(
        "--overwrite",
        help="Delete and recreate the ouput folder if it already exists. WARNING: be careful, there will be no confirmation!",
        action="store_true",
    )
    parser.add_argument(
        "--jobs",
        help="The number of parallel jobs to start. Default to the number of cpu.",
        default=cpu_count(),
        type=int,
    )
    parser.add_argument(
        "--cache_size",
        help="Cache size in MB. Default to available memory / 10.",
        default=int(TOTAL_MEMORY_MB / 10),
        type=int,
    )
    parser.add_argument(
        "--srs_out",
        help="SRS to convert the output with (numeric part of the EPSG code)",
        type=str,
    )
    parser.add_argument(
        "--srs_in", help="Override input SRS (numeric part of the EPSG code)", type=str
    )
    parser.add_argument(
        "--benchmark", help="Print summary at the end of the process", type=str
    )
    parser.add_argument(
        "--no-rgb", help="Don't export rgb attributes", action="store_true"
    )
    parser.add_argument(
        "--classification", help="Export classification attributes", action="store_true"
    )
    parser.add_argument(
        "--intensity",
        help="Export intensity attributes. This support is currently limited to unsigned 8 bits integer for ply files, and to integers for xyz files.",
        action="store_true",
    )
    parser.add_argument("--color_scale", help="Force color scale", type=float)
    parser.add_argument(
        "--force-srs-in",
        help="Force the input srs even if the srs in the input files are different. CAUTION, use only if you know what you are doing.",
        action="store_true",
    )

    return parser


def _main(args: argparse.Namespace) -> None:
    try:
        return convert(
            args.files,
            outfolder=args.out,
            overwrite=args.overwrite,
            jobs=args.jobs,
            cache_size=args.cache_size,
            crs_out=str_to_CRS(args.srs_out),
            crs_in=str_to_CRS(args.srs_in),
            force_crs_in=args.force_srs_in,
            benchmark=args.benchmark,
            rgb=not args.no_rgb,
            classification=args.classification,
            intensity=args.intensity,
            color_scale=args.color_scale,
            verbose=args.verbose,
        )
    except SrsInMissingException:
        print(
            "No SRS information in input files, you should specify it with --srs_in",
            file=sys.stderr,
        )
        sys.exit(EXIT_CODES.MISSING_SRS_IN_FILE.value)
