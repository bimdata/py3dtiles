from __future__ import annotations

import unittest

from py3dtiles.tileset.extension import BaseExtension
from py3dtiles.typing import ExtensionDictType


class MockExtension(BaseExtension):
    @classmethod
    def from_dict(cls, extension_dict: ExtensionDictType) -> MockExtension:
        return cls("MockExtension")

    def to_dict(self) -> ExtensionDictType:
        return {}


class TestExtension(unittest.TestCase):
    def test_constructor(self):
        name = "name"
        extension = MockExtension(name)
        self.assertEqual(extension.name, name)

    def test_to_dict(self):
        extension = MockExtension("name")
        self.assertDictEqual(extension.to_dict(), {})


if __name__ == "__main__":
    unittest.main()
