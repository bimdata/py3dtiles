from enum import Enum


class ManagerMessage(Enum):
    STOP = b"stop"
    SHUTDOWN = b"shutdown"


class WorkerMessageType(Enum):
    IDLE = b"idle"
    HALTED = b"halted"
    ERROR = b"error"
