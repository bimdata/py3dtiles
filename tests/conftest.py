import shutil
from pathlib import Path
from typing import Generator

from pytest import fixture


@fixture()
def tmp_dir() -> Generator[Path, None, None]:
    tmp_dir = Path("tmp/")
    tmp_dir.mkdir()
    yield tmp_dir
    if tmp_dir.exists():
        if tmp_dir.is_dir():
            shutil.rmtree(tmp_dir, ignore_errors=True)
        else:
            tmp_dir.unlink()
