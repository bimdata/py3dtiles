from enum import Enum


class ManagerMessage(Enum):
    """
    Message types sent by the convert function.

    If you create a new tiler, this category of messages is sent by Tiler.
    You cannot inherit this class since it is an enum. Create a new one without these 2 message types.
    """

    STOP = b"stop"
    SHUTDOWN = b"shutdown"


class WorkerMessageType(Enum):
    """
    Message types sent by the broker.

    If you create a new tiler, this category of messages is sent by WorkerTiler.
    You cannot inherit this class. Create a new one without these 3 message types.
    """

    REGISTER = b"register"
    IDLE = b"idle"
    HALTED = b"halted"
    ERROR = b"error"
