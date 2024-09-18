import concurrent.futures
import pickle
import struct
import time
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple, Union

import numpy as np
import numpy.typing as npt
from pyproj import CRS, Transformer

from py3dtiles.exceptions import (
    SrsInMissingException,
    SrsInMixinException,
    TilerException,
)
from py3dtiles.tilers.base_tiler import Tiler
from py3dtiles.tileset.content import read_binary_tile_content
from py3dtiles.tileset.tileset import TileSet
from py3dtiles.utils import (
    READER_MAP,
    compute_spacing,
    make_aabb_valid,
    node_from_name,
    node_name_to_path,
)

from .matrix_manipulation import (
    make_rotation_matrix,
    make_scale_matrix,
    make_translation_matrix,
)
from .node import Node, SharedNodeStore
from .pnts import MIN_POINT_SIZE, pnts_writer
from .point_message_type import PointManagerMessage, PointWorkerMessageType
from .point_shared_metadata import PointSharedMetadata
from .point_state import PointState
from .point_tiler_worker import PointTilerWorker


def is_ancestor(node_name: bytes, ancestor: bytes) -> bool:
    """
    Example, the tile 22 is ancestor of 22458
    Particular case, the tile 22 is ancestor of 22
    """
    return len(ancestor) <= len(node_name) and node_name[0 : len(ancestor)] == ancestor


def is_ancestor_in_list(
    node_name: bytes, ancestors: Union[List[bytes], Dict[bytes, Any]]
) -> bool:
    return any(
        not ancestor or is_ancestor(node_name, ancestor) for ancestor in ancestors
    )


def can_pnts_be_written(
    node_name: bytes,
    finished_node: bytes,
    input_nodes: Union[List[bytes], Dict[bytes, Any]],
    active_nodes: Union[List[bytes], Dict[bytes, Any]],
) -> bool:
    return (
        is_ancestor(node_name, finished_node)
        and not is_ancestor_in_list(node_name, active_nodes)
        and not is_ancestor_in_list(node_name, input_nodes)
    )


class PointTiler(Tiler[PointSharedMetadata, PointTilerWorker]):
    name = b"points"

    file_info: Dict[str, Any]
    root_aabb: npt.NDArray[np.float64]
    root_scale: npt.NDArray[np.float32]
    root_spacing: float
    node_store: SharedNodeStore
    state: PointState

    def __init__(
        self,
        out_folder: Path,
        files: Union[List[Union[str, Path]], str, Path],
        crs_in: Optional[CRS],
        force_crs_in: bool,
        rgb: bool,
        classification: bool,
        intensity: bool,
        color_scale: Optional[float],
        cache_size: int,
        verbosity: int,
    ):
        self.out_folder = out_folder

        # allow str directly if only one input
        files = [files] if isinstance(files, (str, Path)) else files
        self.files = [Path(file) for file in files]

        self.rgb = rgb
        self.classification = classification
        self.intensity = intensity
        self.color_scale = color_scale

        self.crs_in = crs_in
        self.force_crs_in = force_crs_in

        self.cache_size = cache_size

        self.verbosity = verbosity

    def get_worker(self) -> PointTilerWorker:
        return PointTilerWorker(self.shared_metadata)

    def get_tasks(
        self, startup: float
    ) -> Generator[Tuple[bytes, List[bytes]], None, None]:
        while len(self.state.pnts_to_writing) > 0:
            yield self.send_pnts_to_write()

        yield from self.send_points_to_process(time.time() - startup)

        while self.state.can_add_reading_jobs():
            yield self.send_file_to_read()

    def initialization(
        self,
        crs_out: Optional[CRS],
        working_dir: Path,
        number_of_jobs: int,
    ) -> None:
        self.file_info = self.get_file_info(self.crs_in, self.force_crs_in)
        transformer = self.get_transformer(crs_out)
        (
            self.rotation_matrix,
            self.original_aabb,
            self.avg_min,
        ) = self.get_rotation_matrix(crs_out, transformer)

        self.root_aabb, self.root_scale, self.root_spacing = self.get_root_aabb(
            self.original_aabb
        )

        self.node_store = SharedNodeStore(working_dir)

        self.state = PointState(self.file_info["portions"], max(1, number_of_jobs // 2))

        self.shared_metadata = PointSharedMetadata(
            transformer,
            self.root_aabb,
            self.root_spacing,
            self.root_scale,
            self.out_folder,
            self.rgb,
            self.color_scale,
            self.classification,
            self.intensity,
            self.verbosity,
        )

    def get_file_info(
        self,
        crs_in: Optional[CRS],
        force_crs_in: bool = False,
    ) -> Dict[str, Any]:

        pointcloud_file_portions = []
        aabb = None
        total_point_count = 0
        avg_min = np.array([0.0, 0.0, 0.0])

        # read all input files headers and determine the aabb/spacing
        for file in self.files:
            extension = file.suffix
            if extension in READER_MAP:
                reader = READER_MAP[extension]
            else:
                raise ValueError(
                    f"The file with {extension} extension can't be read, "
                    f"the available extensions are: {READER_MAP.keys()}"
                )

            file_info = reader.get_metadata(file)

            pointcloud_file_portions += file_info["portions"]
            if aabb is None:
                aabb = file_info["aabb"]
            else:
                aabb[0] = np.minimum(aabb[0], file_info["aabb"][0])
                aabb[1] = np.maximum(aabb[1], file_info["aabb"][1])

            file_crs_in = file_info["crs_in"]
            if file_crs_in is not None:
                if crs_in is None:
                    crs_in = file_crs_in
                elif crs_in != file_crs_in and not force_crs_in:
                    raise SrsInMixinException(
                        "All input files should have the same srs in, currently there are a mix of"
                        f" {crs_in} and {file_crs_in}"
                    )
            total_point_count += file_info["point_count"]
            avg_min += file_info["avg_min"] / len(self.files)

        # The fact self.files is not empty have been checked before, so this shouldn't happen
        # but this keeps mypy happy and also serve as "defensive programming"
        if aabb is None:
            raise RuntimeError("No aabb could be computed!")
        # correct aabb, so that we don't have null sized box
        # we add 10^-5, supposing it's reasonable for most use case
        make_aabb_valid(aabb)
        return {
            "portions": pointcloud_file_portions,
            "aabb": aabb,
            "crs_in": crs_in,
            "point_count": total_point_count,
            "avg_min": avg_min,
        }

    def get_transformer(self, crs_out: Optional[CRS]) -> Optional[Transformer]:
        if crs_out:
            if self.file_info["crs_in"] is None:
                raise SrsInMissingException(
                    "None file has a input srs specified. Should be provided."
                )

            transformer = Transformer.from_crs(self.file_info["crs_in"], crs_out)
        else:
            transformer = None

        return transformer

    def get_rotation_matrix(
        self, crs_out: Optional[CRS], transformer: Optional[Transformer]
    ) -> Tuple[
        npt.NDArray[np.float64], npt.NDArray[np.float64], npt.NDArray[np.float64]
    ]:
        avg_min: npt.NDArray[np.float64] = self.file_info["avg_min"]
        aabb: npt.NDArray[np.float64] = self.file_info["aabb"]

        rotation_matrix: npt.NDArray[np.float64] = np.identity(4)
        if crs_out is not None and transformer is not None:

            bl: npt.NDArray[np.float64] = np.array(
                list(transformer.transform(aabb[0][0], aabb[0][1], aabb[0][2]))
            )
            tr: npt.NDArray[np.float64] = np.array(
                list(transformer.transform(aabb[1][0], aabb[1][1], aabb[1][2]))
            )
            br: npt.NDArray[np.float64] = np.array(
                list(transformer.transform(aabb[1][0], aabb[0][1], aabb[0][2]))
            )

            avg_min = np.array(
                list(transformer.transform(avg_min[0], avg_min[1], avg_min[2]))
            )

            x_axis = br - bl

            bl = bl - avg_min
            tr = tr - avg_min

            if crs_out.to_epsg() == 4978:
                # Transform geocentric normal => (0, 0, 1)
                # and 4978-bbox x axis => (1, 0, 0),
                # to have a bbox in local coordinates that's nicely aligned with the data
                rotation_matrix = make_rotation_matrix(avg_min, np.array([0, 0, 1]))
                rotation_matrix = np.dot(
                    make_rotation_matrix(x_axis, np.array([1, 0, 0])), rotation_matrix
                )

                rotation_matrix_part = rotation_matrix[:3, :3].T

                bl = np.dot(bl, rotation_matrix_part)
                tr = np.dot(tr, rotation_matrix_part)

            root_aabb = np.array([np.minimum(bl, tr), np.maximum(bl, tr)])
        else:
            # offset
            root_aabb = aabb - avg_min

        return rotation_matrix, root_aabb, avg_min

    def get_root_aabb(
        self, original_aabb: npt.NDArray[np.float64]
    ) -> Tuple[npt.NDArray[np.float64], npt.NDArray[np.float32], float]:
        base_spacing = compute_spacing(original_aabb)
        if base_spacing > 10:
            root_scale = np.array([0.01, 0.01, 0.01])
        elif base_spacing > 1:
            root_scale = np.array([0.1, 0.1, 0.1])
        else:
            root_scale = np.array([1, 1, 1])

        root_aabb = original_aabb * root_scale
        root_spacing = compute_spacing(root_aabb)
        return root_aabb, root_scale, root_spacing

    def print_summary(self) -> None:
        print("Summary:")
        print("  - points to process: {}".format(self.file_info["point_count"]))
        print(f"  - offset to use: {self.avg_min}")
        print(f"  - root spacing: {self.root_spacing / self.root_scale[0]}")
        print(f"  - root aabb: {self.root_aabb}")
        print(f"  - original aabb: {self.original_aabb}")
        print(f"  - scale: {self.root_scale}")

    def send_file_to_read(self) -> Tuple[bytes, List[bytes]]:
        if self.verbosity >= 1:
            print(f"Submit next portion {self.state.point_cloud_file_parts[-1]}")
        file, portion = self.state.point_cloud_file_parts.pop()
        self.state.points_in_progress += portion[1] - portion[0]

        self.state.number_of_reading_jobs += 1

        return PointManagerMessage.READ_FILE.value, [
            pickle.dumps(
                {
                    "filename": file,
                    "offset_scale": (
                        -self.avg_min,
                        self.root_scale,
                        self.rotation_matrix[:3, :3].T,
                    ),
                    "portion": portion,
                }
            ),
        ]

    def send_points_to_process(
        self, now: float
    ) -> Generator[Tuple[bytes, List[bytes]], None, None]:
        potentials = sorted(
            # a key (=task) can be in node_to_process and processing_nodes if the node isn't completely processed
            [
                (node, task)
                for node, task in self.state.node_to_process.items()  # task: [data...], point_count
                if node not in self.state.processing_nodes
            ],
            key=lambda task: -len(task[0]),
        )  # sort by node name size, the root nodes first

        while potentials:
            target_count = 100_000
            job_list = []
            count = 0
            idx = len(potentials) - 1
            while count < target_count and idx >= 0:
                name, (tasks, point_count) = potentials[idx]
                count += point_count
                job_list += [
                    name,
                    self.node_store.get(name),
                    struct.pack(">I", len(tasks)),
                ] + tasks
                del potentials[idx]

                del self.state.node_to_process[name]
                self.state.processing_nodes[name] = (
                    len(tasks),
                    point_count,
                    now,
                )

                if name in self.state.waiting_writing_nodes:
                    self.state.waiting_writing_nodes.pop(
                        self.state.waiting_writing_nodes.index(name)
                    )
                idx -= 1

            if job_list:
                yield PointManagerMessage.PROCESS_JOBS.value, job_list

    def send_pnts_to_write(self) -> Tuple[bytes, List[bytes]]:
        node_name = self.state.pnts_to_writing.pop()
        data = self.node_store.get(node_name)
        if not data:
            raise ValueError(f"{node_name!r} has no data")

        self.node_store.remove(node_name)
        self.state.number_of_writing_jobs += 1

        return PointManagerMessage.WRITE_PNTS.value, [node_name, data]

    def process_message(self, return_type: bytes, result: List[bytes]) -> bool:
        at_least_one_job_ended = False

        if return_type == PointWorkerMessageType.READ.value:
            self.state.number_of_reading_jobs -= 1
            at_least_one_job_ended = True

        elif return_type == PointWorkerMessageType.PROCESSED.value:
            content = pickle.loads(result[-1])
            self.state.processed_points += content["total"]
            self.state.points_in_progress -= content["total"]

            del self.state.processing_nodes[content["name"]]

            self.dispatch_processed_nodes(content)

            at_least_one_job_ended = True

        elif return_type == PointWorkerMessageType.PNTS_WRITTEN.value:
            self.state.points_in_pnts += struct.unpack(">I", result[0])[0]
            self.state.number_of_writing_jobs -= 1

        elif return_type == PointWorkerMessageType.NEW_TASK.value:
            self.state.add_tasks_to_process(
                node_name=result[0],
                data=result[1],
                point_count=struct.unpack(">I", result[2])[0],
            )

        else:
            raise NotImplementedError(f"The command {return_type!r} is not implemented")

        return at_least_one_job_ended

    def dispatch_processed_nodes(self, content: Dict[str, bytes]) -> None:
        if not content["name"]:
            return

        self.node_store.put(content["name"], content["data"])
        self.state.waiting_writing_nodes.append(content["name"])

        if not self.state.is_reading_finish():
            return

        # if all nodes aren't processed yet,
        # we should check if linked ancestors are processed
        if self.state.processing_nodes or self.state.node_to_process:
            finished_node = content["name"]
            if can_pnts_be_written(
                finished_node,
                finished_node,
                self.state.node_to_process,
                self.state.processing_nodes,
            ):
                self.state.waiting_writing_nodes.pop(-1)
                self.state.pnts_to_writing.append(finished_node)

                for i in range(len(self.state.waiting_writing_nodes) - 1, -1, -1):
                    candidate = self.state.waiting_writing_nodes[i]

                    if can_pnts_be_written(
                        candidate,
                        finished_node,
                        self.state.node_to_process,
                        self.state.processing_nodes,
                    ):
                        self.state.waiting_writing_nodes.pop(i)
                        self.state.pnts_to_writing.append(candidate)

        else:
            for c in self.state.waiting_writing_nodes:
                self.state.pnts_to_writing.append(c)
            self.state.waiting_writing_nodes.clear()

    def validate_binary_data(self) -> None:
        if self.state.points_in_pnts != self.file_info["point_count"]:
            raise ValueError(
                "Invalid point count in the written .pnts"
                + f"(expected: {self.file_info['point_count']}, was: {self.state.points_in_pnts})"
            )

    def write_tileset(self) -> None:
        # compute tile transform matrix
        transform = np.linalg.inv(self.rotation_matrix)
        transform = np.dot(transform, make_scale_matrix(1.0 / self.root_scale[0]))
        transform = np.dot(make_translation_matrix(self.avg_min), transform)

        # Create the root tile by sampling (or taking all points?) of child nodes
        root_node = Node(b"", self.root_aabb, self.root_spacing * 2)
        root_node.children = []
        inv_aabb_size = (
            1.0
            / np.maximum(
                MIN_POINT_SIZE,
                self.root_aabb[1] - self.root_aabb[0],
            )
        ).astype(np.float32)
        for child_num in range(8):
            tile_path = node_name_to_path(
                self.out_folder, str(child_num).encode("ascii"), ".pnts"
            )
            if tile_path.exists():
                tile_content = read_binary_tile_content(tile_path)

                fth = tile_content.body.feature_table.header
                xyz = tile_content.body.feature_table.body.position.view(
                    np.float32
                ).reshape((fth.points_length, 3))
                if self.rgb:
                    tile_color = tile_content.body.feature_table.body.color
                    if tile_color is None:
                        raise TilerException(
                            "tile_content.body.feature_table.body.color shouldn't be None here. Seems to be a py3dtiles issue."
                        )
                    if tile_color.dtype != np.uint8:
                        raise TilerException(
                            "The data type of tile_content.body.feature_table.body.color must be np.uint8. Seems to be a py3dtiles issue."
                        )
                    rgb = tile_color.reshape((fth.points_length, 3)).astype(
                        np.uint8, copy=False
                    )  # the astype is used for typing
                else:
                    rgb = np.zeros(xyz.shape, dtype=np.uint8)
                if self.classification:
                    classification = (
                        tile_content.body.batch_table.get_binary_property(
                            "Classification"
                        )
                        .astype(np.uint8)
                        .reshape(-1, 1)
                    )
                else:
                    classification = np.zeros((fth.points_length, 1), dtype=np.uint8)

                if self.intensity:
                    intensity = (
                        (tile_content.body.batch_table.get_binary_property("Intensity"))
                        .astype(np.uint8)
                        .reshape(-1, 1)
                    )
                else:
                    intensity = np.zeros((fth.points_length, 1), dtype=np.uint8)

                root_node.grid.insert(
                    self.root_aabb[0].astype(np.float32),
                    inv_aabb_size,
                    xyz.copy(),
                    rgb,
                    classification,
                    intensity,
                )

        pnts_writer.node_to_pnts(
            b"",
            root_node,
            self.out_folder,
            self.rgb,
            self.classification,
            self.intensity,
        )

        pool_executor = concurrent.futures.ProcessPoolExecutor()
        root_tile = node_from_name(b"", self.root_aabb, self.root_spacing).to_tileset(
            self.out_folder, self.root_scale, None, 0, pool_executor
        )
        pool_executor.shutdown()

        if root_tile is None:
            raise RuntimeError(
                "root_tileset cannot be None here. This is likely a tiler bug."
            )

        root_tile.transform = transform.reshape(16, order="F")
        root_tile.set_refine_mode(
            "REPLACE"
        )  # The root tile is in the "REPLACE" refine mode
        # And children with the "ADD" refine mode
        # No need to set this property in their children, they will take the parent value if it is not present
        for child in root_tile.children:
            child.set_refine_mode("ADD")

        geometric_error = (
            np.linalg.norm(self.root_aabb[1] - self.root_aabb[0]) / self.root_scale[0]
        )
        tileset = TileSet(geometric_error=geometric_error)
        tileset.root_tile = root_tile
        tileset.write_as_json(self.out_folder / "tileset.json")

    def benchmark(self, benchmark_id: str, startup: float) -> None:
        print(
            "{},{},{},{}".format(
                self.benchmark,
                ",".join([f.name for f in self.files]),
                self.state.points_in_pnts,
                round(time.time() - startup, 1),
            )
        )

    def print_debug(
        self, now: float, number_of_jobs: int, number_of_idle_clients: int
    ) -> None:
        if self.verbosity >= 3:
            print("{:^16}|{:^8}|{:^8}".format("Name", "Points", "Seconds"))
            for name, v in self.state.processing_nodes.items():
                print(
                    "{:^16}|{:^8}|{:^8}".format(
                        "{} ({})".format(name.decode("ascii"), v[0]),
                        v[1],
                        round(now - v[2], 1),
                    )
                )
            print("")
            print("Pending:")
            print(
                "  - root: {} / {}".format(
                    len(self.state.point_cloud_file_parts),
                    self.state.initial_portion_count,
                )
            )
            print(
                "  - other: {} files for {} nodes".format(
                    sum([len(f[0]) for f in self.state.node_to_process.values()]),
                    len(self.state.node_to_process),
                )
            )
            print("")

        elif self.verbosity >= 2:
            self.state.print_debug()

        if self.verbosity >= 1:
            print(
                "{} % points in {} sec [{} tasks, {} nodes, {} wip]".format(
                    round(
                        100
                        * self.state.processed_points
                        / self.file_info["point_count"],
                        2,
                    ),
                    round(now, 1),
                    number_of_jobs - number_of_idle_clients,
                    len(self.state.processing_nodes),
                    self.state.points_in_progress,
                )
            )

        elif self.verbosity >= 0:
            percent = round(
                100 * self.state.processed_points / self.file_info["point_count"],
                2,
            )
            time_left = (100 - percent) * now / (percent + 0.001)
            print(
                f"\r{percent:>6} % in {round(now)} sec [est. time left: {round(time_left)} sec]      ",
                end="",
                flush=True,
            )

    def memory_control(self) -> None:
        self.node_store.control_memory_usage(self.cache_size, self.verbosity)
