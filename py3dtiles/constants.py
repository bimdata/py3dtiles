from enum import Enum


class EXIT_CODES(Enum):
    SUCCESS = 0
    MISSING_DEPS = 1
    MISSING_ARGS = 2
    UNSPECIFIED_ERROR = 3
    MISSING_SRS_IN_FILE = 10
