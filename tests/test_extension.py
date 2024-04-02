from __future__ import annotations

from pathlib import Path

from py3dtiles.tileset import TileSet
from py3dtiles.tileset.extension import (
    BaseExtension,
    create_extension,
    is_extension_registered,
    register_extension,
)

from .fixtures.mock_extension import MockExtension

DATA_DIRECTORY = Path(__file__).parent / "fixtures"


def test_constructor() -> None:
    name = "name"
    extension = MockExtension(name)
    assert extension.name == name


def test_to_dict() -> None:
    extension = MockExtension("name")
    assert extension.to_dict() == {}


def test_from_dict() -> None:
    extension_data = {"a": 10, "b": "name", "c": [0, 1, 2]}
    extension = BaseExtension.from_dict(extension_data)

    assert isinstance(extension, BaseExtension)
    assert extension.attributes == extension_data


def test_register() -> None:
    register_extension("MockExtension", MockExtension)

    assert is_extension_registered("MockExtension")


def test_create() -> None:
    register_extension("MockExtension", MockExtension)
    mock_extension = create_extension("MockExtension", {})
    some_extension = create_extension("SomeExtension", {})

    assert is_extension_registered("MockExtension")
    assert isinstance(mock_extension, MockExtension)
    assert not is_extension_registered("SomeExtension")
    assert isinstance(some_extension, BaseExtension)


def test_unregistered_extension() -> None:
    path = Path(DATA_DIRECTORY, "tileset_with_extension.json")

    assert path.exists()

    tileset = TileSet.from_file(path)

    assert "Test" in tileset.extensions
    assert isinstance(tileset.extensions["Test"], BaseExtension)
    assert tileset.extensions["Test"].to_dict() == {"id": "IDTS00"}
    assert "Test" in tileset.root_tile.extensions
    assert isinstance(tileset.root_tile.extensions["Test"], BaseExtension)
    assert tileset.root_tile.extensions["Test"].to_dict() == {"id": "IDT00"}
    assert "Test" in tileset.root_tile.bounding_volume.extensions  # type: ignore
    assert isinstance(tileset.root_tile.bounding_volume.extensions["Test"], BaseExtension)  # type: ignore
    assert tileset.root_tile.bounding_volume.extensions["Test"].to_dict() == {"id": "IDBB00"}  # type: ignore

    tile_content = tileset.root_tile.get_or_fetch_content(tileset.root_uri)
    batch_table_data = tile_content.body.batch_table.header.data  # type: ignore

    assert "extensions" in batch_table_data
    assert "MockExtension" in batch_table_data["extensions"]
    assert batch_table_data["extensions"]["MockExtension"] == {  # type: ignore
        "color": ["black", "white"],
        "height": [10, 15],
    }
    assert "extras" in batch_table_data
    assert "description" in batch_table_data["extras"]
    assert batch_table_data["extras"]["description"] == "tile with mock extension"  # type: ignore
