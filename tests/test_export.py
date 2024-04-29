import json
import shutil
from pathlib import Path
from typing import Generator

from pytest import fixture

from py3dtiles.export import from_directory

DATA_DIRECTORY = Path(__file__).parent / "fixtures"


@fixture()
def tmp_dir() -> Generator[Path, None, None]:
    yield Path("tmp/")
    shutil.rmtree("tmp/", ignore_errors=True)


def test_export(tmp_dir: Path) -> None:
    tmp_dir.mkdir()
    from_directory(DATA_DIRECTORY / "building", offset=None, output_dir=tmp_dir)

    # basic asserts
    tileset_path = tmp_dir / "tileset.json"
    with tileset_path.open() as f:
        tileset = json.load(f)

    expecting_box = [0.028, 2.054, -0.028, 8.776, 0, 0, 0, 0.0, 0, 0, 0, 7.327]
    box = [round(value, 4) for value in tileset["root"]["boundingVolume"]["box"]]
    assert box == expecting_box

    assert Path(tmp_dir, "tiles", "1.b3dm").exists()
