import shutil
from pathlib import Path
from typing import Generator

from pytest import fixture


@fixture()
def tmp_dir() -> Generator[Path, None, None]:
    tmp_dir = Path("tmp/")
    tmp_dir.mkdir()
    yield tmp_dir
    shutil.rmtree("tmp/", ignore_errors=True)
