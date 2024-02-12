from enum import Enum


class PointManagerMessage(Enum):
    READ_FILE = b"read_file"
    WRITE_PNTS = b"write_pnts"
    PROCESS_JOBS = b"process_job"


class PointWorkerMessageType(Enum):
    READ = b"read"
    PROCESSED = b"processed"
    PNTS_WRITTEN = b"pnts_written"
    NEW_TASK = b"new_task"
