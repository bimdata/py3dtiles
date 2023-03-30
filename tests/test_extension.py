from __future__ import annotations

from .fixtures.mock_extension import MockExtension


def test_constructor():
    name = "name"
    extension = MockExtension(name)
    assert extension.name == name


def test_to_dict():
    extension = MockExtension("name")
    assert extension.to_dict() == {}
