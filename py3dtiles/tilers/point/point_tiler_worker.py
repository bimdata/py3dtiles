import os
import pickle
import struct
import time
from pathlib import PurePath
from typing import List

import zmq

from py3dtiles.tilers.base_tiler import TilerWorker
from py3dtiles.utils import READER_MAP

from .node import NodeCatalog, NodeProcess
from .pnts import pnts_writer
from .point_message_type import PointManagerMessage, PointWorkerMessageType
from .point_shared_metadata import PointSharedMetadata


class PointTilerWorker(TilerWorker[PointSharedMetadata]):
    def execute(
        self, skt: zmq.Socket[bytes], command: bytes, content: List[bytes]
    ) -> None:
        if command == PointManagerMessage.READ_FILE.value:
            self.execute_read_file(skt, content)
        elif command == PointManagerMessage.PROCESS_JOBS.value:
            self.execute_process_jobs(skt, content)
        elif command == PointManagerMessage.WRITE_PNTS.value:
            self.execute_write_pnts(skt, content[1], content[0])
        else:
            raise NotImplementedError(f"Unknown command {command!r}")

    def execute_read_file(self, skt: zmq.Socket[bytes], content: List[bytes]) -> None:
        parameters = pickle.loads(content[0])

        extension = PurePath(parameters["filename"]).suffix
        if extension in READER_MAP:
            reader = READER_MAP[extension]
        else:
            raise ValueError(
                f"The file with {extension} extension can't be read, "
                f"the available extensions are: {READER_MAP.keys()}"
            )

        reader_gen = reader.run(
            parameters["filename"],
            parameters["offset_scale"],
            parameters["portion"],
            self.shared_metadata.transformer,
            self.shared_metadata.color_scale,
            self.shared_metadata.write_intensity,
        )
        for coords, colors, classification, intensity in reader_gen:
            skt.send_multipart(
                [
                    PointWorkerMessageType.NEW_TASK.value,
                    b"",
                    pickle.dumps(
                        {
                            "xyz": coords,
                            "rgb": colors,
                            "classification": classification,
                            "intensity": intensity,
                        }
                    ),
                    struct.pack(">I", len(coords)),
                ],
                copy=False,
            )

        skt.send_multipart([PointWorkerMessageType.READ.value])

    def execute_write_pnts(
        self, skt: zmq.Socket[bytes], content: bytes, node_name: bytes
    ) -> None:
        pnts_writer_gen = pnts_writer.run(
            content,
            self.shared_metadata.out_folder,
            self.shared_metadata.write_rgb,
            self.shared_metadata.write_classification,
            self.shared_metadata.write_intensity,
        )
        for total in pnts_writer_gen:
            skt.send_multipart(
                [
                    PointWorkerMessageType.PNTS_WRITTEN.value,
                    struct.pack(">I", total),
                    node_name,
                ]
            )

    def execute_process_jobs(
        self, skt: zmq.Socket[bytes], content: List[bytes]
    ) -> None:
        begin = time.time()
        log_enabled = self.shared_metadata.verbosity >= 2
        if log_enabled:
            log_filename = f"py3dtiles-{os.getpid()}.log"
            log_file = open(log_filename, "a")
        else:
            log_file = None

        i = 0
        while i < len(content):
            name = content[i]
            node = content[i + 1]
            count = struct.unpack(">I", content[i + 2])[0]
            tasks = content[i + 3 : i + 3 + count]
            i += 3 + count

            node_catalog = NodeCatalog(
                node,
                name,
                self.shared_metadata.root_aabb,
                self.shared_metadata.root_spacing,
            )

            node_process = NodeProcess(
                node_catalog,
                self.shared_metadata.scale[0],
                name,
                tasks,
                begin,
                log_file,
            )
            for proc_name, proc_data, proc_point_count in node_process.run():
                skt.send_multipart(
                    [
                        PointWorkerMessageType.NEW_TASK.value,
                        proc_name,
                        proc_data,
                        struct.pack(">I", proc_point_count),
                    ],
                    copy=False,
                    block=False,
                )

            if log_enabled:
                print(f"save on disk {name!r} [{time.time() - begin}]", file=log_file)

            # save node state on disk
            if len(name) > 0:
                data = node_catalog.dump(name, node_process.infer_depth_from_name() - 1)
            else:
                data = b""

            if log_enabled:
                print(f"saved on disk [{time.time() - begin}]", file=log_file)

            skt.send_multipart(
                [
                    PointWorkerMessageType.PROCESSED.value,
                    pickle.dumps(
                        {
                            "name": name,
                            "total": node_process.total_point_count,
                            "data": data,
                        }
                    ),
                ],
                copy=False,
            )

        if log_enabled:
            print(
                "[<] return result [{} sec] [{}]".format(
                    round(time.time() - begin, 2), time.time() - begin
                ),
                file=log_file,
                flush=True,
            )
            if log_file is not None:
                log_file.close()
