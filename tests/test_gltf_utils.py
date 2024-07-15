import numpy as np
import pygltflib
from pytest import raises

from py3dtiles.tileset.content.gltf_utils import get_component_type_from_dtype


def test_component_type_from_dtype() -> None:
    assert get_component_type_from_dtype(np.dtype(np.int8)) == pygltflib.BYTE
    assert get_component_type_from_dtype(np.dtype(np.uint8)) == pygltflib.UNSIGNED_BYTE
    assert get_component_type_from_dtype(np.dtype(np.int16)) == pygltflib.SHORT
    assert (
        get_component_type_from_dtype(np.dtype(np.uint16)) == pygltflib.UNSIGNED_SHORT
    )
    assert get_component_type_from_dtype(np.dtype(np.uint32)) == pygltflib.UNSIGNED_INT
    assert get_component_type_from_dtype(np.dtype(np.float32)) == pygltflib.FLOAT
    with raises(
        ValueError,
        match="Cannot find a component type suitable for float64",
    ):
        get_component_type_from_dtype(np.dtype(np.float64))
