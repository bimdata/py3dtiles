from typing import Dict, List, Tuple

from py3dtiles.typing import PortionsType


class PointState:
    def __init__(
        self, pointcloud_file_portions: PortionsType, max_reading_jobs: int
    ) -> None:
        self.processed_points = 0
        self.max_point_in_progress = 60_000_000
        self.points_in_progress = 0
        self.points_in_pnts = 0

        # pointcloud_file_portions is a list of tuple (filename, (start offset, end offset))
        self.point_cloud_file_parts = pointcloud_file_portions
        self.initial_portion_count = len(pointcloud_file_portions)
        self.max_reading_jobs = max_reading_jobs
        self.number_of_reading_jobs = 0
        self.number_of_writing_jobs = 0

        # node_to_process is a dictionary of tasks,
        # each entry is a tile identified by its name (a string of numbers)
        # so for each entry, it is a list of tasks
        # a task is a tuple (list of points, point_count)
        # points is a dictionary {xyz: list of coordinates, color: the associated color}
        self.node_to_process: Dict[bytes, Tuple[List[bytes], int]] = {}
        # when a node is sent to a process, the item moves to processing_nodes
        # the structure is different. The key remains the node name. But the value is : (len(tasks), point_count, now)
        # these values is for logging
        self.processing_nodes: Dict[bytes, Tuple[int, int, float]] = {}
        # when processing is finished, move the tile name in processed_nodes
        # since the content is at this stage, stored in the node_store,
        # just keep the name of the node.
        # This list will be filled until the writing could be started.
        self.waiting_writing_nodes: List[bytes] = []
        # when the node is writing, its name is moved from waiting_writing_nodes to pnts_to_writing
        # the data to write are stored in a node object.
        self.pnts_to_writing: List[bytes] = []

    def is_reading_finish(self) -> bool:
        return not self.point_cloud_file_parts and self.number_of_reading_jobs == 0

    def add_tasks_to_process(
        self, node_name: bytes, data: bytes, point_count: int
    ) -> None:
        if point_count <= 0:
            raise ValueError(
                "point_count should be strictly positive, currently", point_count
            )

        if node_name not in self.node_to_process:
            self.node_to_process[node_name] = ([data], point_count)
        else:
            tasks, count = self.node_to_process[node_name]
            tasks.append(data)
            self.node_to_process[node_name] = (tasks, count + point_count)

    def can_add_reading_jobs(self) -> bool:
        return bool(
            self.point_cloud_file_parts
            and self.points_in_progress < self.max_point_in_progress
            and self.number_of_reading_jobs < self.max_reading_jobs
        )

    def print_debug(self) -> None:
        print("{:^16}|{:^8}|{:^8}|{:^8}".format("Step", "Input", "Active", "Inactive"))
        print(
            "{:^16}|{:^8}|{:^8}|{:^8}".format(
                "Reader",
                len(self.point_cloud_file_parts),
                self.number_of_reading_jobs,
                "",
            )
        )
        print(
            "{:^16}|{:^8}|{:^8}|{:^8}".format(
                "Node process",
                len(self.node_to_process),
                len(self.processing_nodes),
                len(self.waiting_writing_nodes),
            )
        )
        print(
            "{:^16}|{:^8}|{:^8}|{:^8}".format(
                "Pnts writer",
                len(self.pnts_to_writing),
                self.number_of_writing_jobs,
                "",
            )
        )
