from __future__ import annotations

from typing import NamedTuple

import numpy as np
import numpy.typing as npt
import pygltflib


class GltfAttribute(NamedTuple):
    name: str
    accessor_type: pygltflib.SCALAR | pygltflib.VEC2 | pygltflib.VEC3
    component_type: pygltflib.UNSIGNED_BYTE | pygltflib.UNSIGNED_INT | pygltflib.FLOAT
    array: npt.NDArray[np.uint8] | npt.NDArray[np.float32] | npt.NDArray[np.uint32]


class GltfPrimitive:
    def __init__(
        self,
        points: npt.NDArray[np.float32],
        triangles: npt.NDArray[np.uint8],
        normals: npt.NDArray[np.float32] | None = None,
        uvs: npt.NDArray[np.float32] | None = None,
        batchids: npt.NDArray[np.uint32] | None = None,
        additional_attributes: list[GltfAttribute] | None = None,
        texture_uri: str | None = None,
        material: pygltflib.Material | None = None,
    ) -> None:
        self.points: GltfAttribute = GltfAttribute(
            "POSITION", pygltflib.VEC3, pygltflib.FLOAT, points
        )
        self.triangles: GltfAttribute = GltfAttribute(
            "INDICE", pygltflib.SCALAR, pygltflib.UNSIGNED_BYTE, triangles
        )
        self.normals: GltfAttribute | None = (
            GltfAttribute("NORMAL", pygltflib.VEC3, pygltflib.FLOAT, normals)
            if normals is not None
            else None
        )
        self.uvs: GltfAttribute | None = (
            GltfAttribute("TEXCOORD_0", pygltflib.VEC2, pygltflib.FLOAT, uvs)
            if uvs is not None
            else None
        )
        self.batchids: GltfAttribute | None = (
            GltfAttribute(
                "_BATCHID", pygltflib.SCALAR, pygltflib.UNSIGNED_INT, batchids
            )
            if batchids is not None
            else None
        )
        self.additional_attributes: list[GltfAttribute] = (
            additional_attributes if additional_attributes is not None else []
        )
        self.texture_uri: str | None = texture_uri
        self.material: pygltflib.Material | None = material


def gltf_component_from_primitive(
    primitive: GltfPrimitive,
    byte_offset: int = 0,
    attribute_counter: int = 0,
) -> tuple[
    pygltflib.Primitive, list[pygltflib.Accessor], list[pygltflib.BufferView], bytes
]:
    """Build the GlTF structure that corresponds to a triangulated mesh.

    The mesh is represented as numpy arrays as follows:

    - a 3D-point array;
    - a triangle array, where points are identified by their positional ID in the 3D-point
      array.

    See https://gitlab.com/dodgyville/pygltflib/ (section "Create a mesh, convert to bytes,
    convert back to mesh").

    """
    gltf_primitive = pygltflib.Primitive(
        attributes=pygltflib.Attributes(),
        indices=attribute_counter,
    )

    indice_blob, indice_accessor, indice_buffer_view = prepare_gltf_component(
        attribute_counter,
        primitive.triangles.array,
        byte_offset,
        primitive.triangles.array.size,
        primitive.triangles.accessor_type,
        primitive.triangles.component_type,
        pygltflib.ELEMENT_ARRAY_BUFFER,
    )
    gltf_binary_blob = indice_blob
    gltf_accessors = [indice_accessor]
    gltf_buffer_views = [indice_buffer_view]
    attribute_counter += 1

    attributes_array: list[GltfAttribute | None] = [
        primitive.points,
        primitive.normals,
        primitive.uvs,
        primitive.batchids,
    ]
    attributes_array.extend(primitive.additional_attributes)

    for attribute in attributes_array:
        if attribute is None:
            continue
        (array_blob, accessor, buffer_view,) = prepare_gltf_component(
            attribute_counter,
            attribute.array,
            byte_offset + len(gltf_binary_blob),
            len(attribute.array),
            attribute.accessor_type,
            attribute.component_type,
        )
        gltf_binary_blob += array_blob
        gltf_accessors.append(accessor)
        gltf_buffer_views.append(buffer_view)
        setattr(gltf_primitive.attributes, attribute.name, attribute_counter)
        attribute_counter += 1

    gltf_accessors[1].min = np.min(primitive.points.array, axis=0).tolist()
    gltf_accessors[1].max = np.max(primitive.points.array, axis=0).tolist()

    return gltf_primitive, gltf_accessors, gltf_buffer_views, gltf_binary_blob


def prepare_gltf_component(
    array_idx: int,
    array: npt.NDArray[np.uint8] | npt.NDArray[np.float32] | npt.NDArray[np.uint32],
    byte_offset: int,
    count: int,
    accessor_type: str = pygltflib.VEC3,
    component_type: int = pygltflib.FLOAT,
    buffer_view_target: int = pygltflib.ARRAY_BUFFER,
) -> tuple[bytes, pygltflib.Accessor, pygltflib.BufferView]:
    array_blob = array.flatten().tobytes()
    BUFFER_INDEX = 0  # Everything is stored in the same buffer for sake of simplicity
    accessor = pygltflib.Accessor(
        bufferView=array_idx,
        componentType=component_type,
        count=count,
        type=accessor_type,
    )
    buffer_view = pygltflib.BufferView(
        buffer=BUFFER_INDEX,
        byteOffset=byte_offset,
        byteLength=len(array_blob),
        target=buffer_view_target,
    )
    return array_blob, accessor, buffer_view
