from __future__ import annotations

from py3dtiles.typing import ExtensionDictType

registered_extensions: dict[str, type[BaseExtension]] = {}


class BaseExtension:
    """
    A base class to manage 3dtiles extension.

    If an extension is added somewhere in a tileset,
    the user must add the name of the extension in the attribute `extensions_used` of the class `TileSet`.
    Also, if the support of an extension is necessary to display the tileset,
    the name must be added in the attribute `extensions_required` of the class `TileSet`.
    """

    def __init__(self, name: str):
        self.name = name
        self.attributes: ExtensionDictType = {}

    @classmethod
    def from_dict(cls, extension_dict: ExtensionDictType) -> BaseExtension:
        """
        Creates an instance of the default extension class BaseExtension. This instance will store all attributes in a single field.

        :param extension_dict: a dict containing all attributes of the extension (keys and values).
        :return: a BaseExtension instance.
        """
        extension = cls("")
        extension.attributes = extension_dict
        return extension

    def to_dict(self) -> ExtensionDictType:
        """
        :return: a dict containing all attributes of the extension (keys and values).
        """
        return self.attributes


def create_extension(
    extension_key: str, extension_dict: ExtensionDictType
) -> BaseExtension:
    """
    Creates an instance of the extension if it is registered.
    Else, creates an instance of BaseExtension storing all attributes in a single field.

    :param extension_key: the name of the extension to create
    :param extension_dict: a dict containing all attributes of the extension (keys and values).
    :return: an extension.
    """
    extension_class = registered_extensions.get(extension_key, BaseExtension)
    return extension_class.from_dict(extension_dict)


def register_extension(
    extension_key: str, extension_class: type[BaseExtension]
) -> None:
    """
    Registers an extension by mapping the name of the extension with the corresponding class.

    :param extension_key: the name of the extension as a string.
    :param extension_class: the class of the extension.
    """
    registered_extensions[extension_key] = extension_class


def is_extension_registered(extension_key: str) -> bool:
    """
    Checks if the extension is registered.

    :param extension_key: the name of the extension as a string.
    :return: a boolean.
    """
    return extension_key in registered_extensions
