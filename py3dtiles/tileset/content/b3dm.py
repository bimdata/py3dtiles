from __future__ import annotations

import struct

import numpy as np
import numpy.typing as npt
import pygltflib

from py3dtiles.exceptions import InvalidB3dmError

from .b3dm_feature_table import B3dmFeatureTable
from .batch_table import BatchTable
from .tile_content import TileContent, TileContentBody, TileContentHeader


class B3dm(TileContent):
    def __init__(self, header: B3dmHeader, body: B3dmBody) -> None:
        super().__init__()

        self.header: B3dmHeader = header
        self.body: B3dmBody = body

    def sync(self) -> None:
        """
        Allow to synchronize headers with contents.
        """

        # extract array
        self.body.gltf.set_min_alignment(8)
        gltf_arr = np.frombuffer(
            b"".join(self.body.gltf.save_to_bytes()), dtype=np.uint8
        )

        # sync the tile header with feature table contents
        self.header.tile_byte_length = len(gltf_arr) + B3dmHeader.BYTE_LENGTH
        self.header.bt_json_byte_length = 0
        self.header.bt_bin_byte_length = 0
        self.header.ft_json_byte_length = 0
        self.header.ft_bin_byte_length = 0

        if self.body.feature_table is not None:
            fth_arr = self.body.feature_table.to_array()

            self.header.tile_byte_length += len(fth_arr)
            self.header.ft_json_byte_length = len(fth_arr)

        if self.body.batch_table is not None:
            bth_arr = self.body.batch_table.to_array()

            self.header.tile_byte_length += len(bth_arr)
            self.header.bt_json_byte_length = len(bth_arr)

    @staticmethod
    def from_numpy_arrays(
        points: npt.NDArray[np.float32],
        triangles: npt.NDArray[np.uint8],
        batch_table: BatchTable | None = None,
        feature_table: B3dmFeatureTable | None = None,
        normal: npt.NDArray[np.float32] | None = None,
        uvs: npt.NDArray[np.float32] | None = None,
        batchids: npt.NDArray[np.uint32] | None = None,
        transform: npt.NDArray[np.float32] | None = None,
        texture_uri: str | None = None,
    ) -> B3dm:
        b3dm_header = B3dmHeader()
        b3dm_body = B3dmBody.from_numpy_arrays(
            points, triangles, normal, uvs, batchids, transform, texture_uri
        )
        if batch_table is not None:
            b3dm_body.batch_table = batch_table
        if feature_table is not None:
            b3dm_body.feature_table = feature_table
        b3dm = B3dm(b3dm_header, b3dm_body)
        b3dm.sync()
        return b3dm

    @staticmethod
    def from_gltf(
        gltf: pygltflib.GLTF2,
        batch_table: BatchTable | None = None,
        feature_table: B3dmFeatureTable | None = None,
    ) -> B3dm:
        b3dm_body = B3dmBody()
        b3dm_body.gltf = gltf
        if batch_table is not None:
            b3dm_body.batch_table = batch_table
        if feature_table is not None:
            b3dm_body.feature_table = feature_table

        b3dm_header = B3dmHeader()
        b3dm = B3dm(b3dm_header, b3dm_body)
        b3dm.sync()

        return b3dm

    @staticmethod
    def from_array(array: npt.NDArray[np.uint8]) -> B3dm:
        # build tile header
        h_arr = array[: B3dmHeader.BYTE_LENGTH]
        b3dm_header = B3dmHeader.from_array(h_arr)

        if b3dm_header.tile_byte_length != len(array):
            raise InvalidB3dmError(
                f"Invalid byte length in header, the size of array is {len(array)}, "
                f"the tile_byte_length for header is {b3dm_header.tile_byte_length}"
            )

        # build tile body
        b_arr = array[B3dmHeader.BYTE_LENGTH :]
        b3dm_body = B3dmBody.from_array(b3dm_header, b_arr)
        b3dm = B3dm(b3dm_header, b3dm_body)
        b3dm.sync()

        return b3dm


class B3dmHeader(TileContentHeader):
    BYTE_LENGTH = 28

    def __init__(self) -> None:
        super().__init__()
        self.magic_value = b"b3dm"
        self.version = 1

    def to_array(self) -> npt.NDArray[np.uint8]:
        header_arr = np.frombuffer(self.magic_value, np.uint8)

        header_arr2 = np.array(
            [
                self.version,
                self.tile_byte_length,
                self.ft_json_byte_length,
                self.ft_bin_byte_length,
                self.bt_json_byte_length,
                self.bt_bin_byte_length,
            ],
            dtype=np.uint32,
        )

        return np.concatenate((header_arr, header_arr2.view(np.uint8)))

    @staticmethod
    def from_array(array: npt.NDArray[np.uint8]) -> B3dmHeader:
        h = B3dmHeader()

        if len(array) != B3dmHeader.BYTE_LENGTH:
            raise InvalidB3dmError(
                f"Invalid header byte length, the size of array is {len(array)}, "
                f"the header must have a size of {B3dmHeader.BYTE_LENGTH}"
            )

        h.version = struct.unpack("i", array[4:8].tobytes())[0]
        h.tile_byte_length = struct.unpack("i", array[8:12].tobytes())[0]
        h.ft_json_byte_length = struct.unpack("i", array[12:16].tobytes())[0]
        h.ft_bin_byte_length = struct.unpack("i", array[16:20].tobytes())[0]
        h.bt_json_byte_length = struct.unpack("i", array[20:24].tobytes())[0]
        h.bt_bin_byte_length = struct.unpack("i", array[24:28].tobytes())[0]

        return h


class B3dmBody(TileContentBody):
    def __init__(self) -> None:
        self.batch_table = BatchTable()
        self.feature_table: B3dmFeatureTable = B3dmFeatureTable()
        self.gltf = pygltflib.GLTF2()

    def __str__(self) -> str:
        gltf_byte_components = self.gltf.save_to_bytes()
        infos = {
            "feature_table_batch_length": self.feature_table.get_batch_length(),
            "gltf_magic": pygltflib.MAGIC,
            "gltf_version": self.gltf.asset.version,
            "gltf_length": len(b"".join(gltf_byte_components)),
            "gltf_json_chunk_length": len(gltf_byte_components[5]),
            "gltf_bin_chunk_length": len(gltf_byte_components[-1]),
        }
        return "\n".join(f"{key}: {value}" for key, value in infos.items())

    def to_array(self) -> npt.NDArray[np.uint8]:
        if self.feature_table:
            feature_table = self.feature_table.to_array()
        else:
            feature_table = np.array([], dtype=np.uint8)

        if self.batch_table:
            batch_table = self.batch_table.to_array()
        else:
            batch_table = np.array([], dtype=np.uint8)

        # The glTF part must start and end on an 8-byte boundary
        return np.concatenate(
            (
                feature_table,
                batch_table,
                np.frombuffer(b"".join(self.gltf.save_to_bytes()), dtype=np.uint8),
            )
        )

    @staticmethod
    def from_numpy_arrays(
        points: npt.NDArray[np.float32],
        triangles: npt.NDArray[np.uint8],
        normals: npt.NDArray[np.float32] | None = None,
        uvs: npt.NDArray[np.float32] | None = None,
        batchids: npt.NDArray[np.uint32] | None = None,
        transform: npt.NDArray[np.float32] | None = None,
        texture_uri: str | None = None,
    ) -> B3dmBody:
        """Build the GlTF structure that corresponds to a triangulated mesh.

        The mesh is represented as numpy arrays as follows:

        - a 3D-point array;
        - a triangle array, where points are identified by their positional ID in the 3D-point
          array.

        See https://gitlab.com/dodgyville/pygltflib/ (section "Create a mesh, convert to bytes,
        convert back to mesh").

        """
        gltf_binary_blob = b""
        gltf_accessors = []
        gltf_buffer_views = []
        byte_offset = 0

        triangle_arrays: list[
            npt.NDArray[np.uint8]
            | npt.NDArray[np.float32]
            | npt.NDArray[np.uint32]
            | None
        ] = [triangles, points, normals, uvs, batchids]
        array_idx = 0
        for array in triangle_arrays:
            if array is None:
                continue
            (
                array_blob,
                additional_offset,
                accessor,
                buffer_view,
            ) = prepare_gltf_component(
                array_idx, array, byte_offset, triangle_indices=array_idx == 0
            )
            gltf_binary_blob += array_blob
            byte_offset += additional_offset
            gltf_accessors.append(accessor)
            gltf_buffer_views.append(buffer_view)
            array_idx += 1

        node_matrix = list(np.identity(4).flatten("F"))
        if transform is not None:
            node_matrix = list(transform.flatten("F"))

        counter = 1
        position_index = counter
        counter += 1
        normal_index = None
        if normals is not None:
            normal_index = counter
            counter += 1
        uvs_index = None
        if uvs is not None:
            uvs_index = counter
            counter += 1
        batchids_index = None
        if batchids is not None:
            batchids_index = counter
            counter += 1

        gltf = pygltflib.GLTF2(
            scene=0,
            scenes=[pygltflib.Scene(nodes=[0])],
            nodes=[pygltflib.Node(mesh=0, matrix=node_matrix)],
            meshes=[
                pygltflib.Mesh(
                    primitives=[
                        pygltflib.Primitive(
                            attributes=pygltflib.Attributes(
                                POSITION=position_index,
                                NORMAL=normal_index,
                                TEXCOORD_0=uvs_index,
                                _BATCHID=batchids_index,
                            ),
                            indices=0,
                            material=0,
                        )
                    ]
                )
            ],
            accessors=gltf_accessors,
            bufferViews=gltf_buffer_views,
            buffers=[pygltflib.Buffer(byteLength=byte_offset)],
        )
        gltf_accessors[position_index].min = np.min(points, axis=0).tolist()
        gltf_accessors[position_index].max = np.max(points, axis=0).tolist()
        base_color_texture = None if uvs is None else pygltflib.TextureInfo(index=0)
        gltf.materials.append(
            pygltflib.Material(
                pbrMetallicRoughness=pygltflib.PbrMetallicRoughness(
                    baseColorTexture=base_color_texture
                )
            )
        ),
        if uvs is not None:
            gltf.textures.append(pygltflib.Texture(sampler=0, source=0))
            gltf.samplers.append(
                pygltflib.Sampler(
                    magFilter=pygltflib.LINEAR,
                    minFilter=pygltflib.LINEAR_MIPMAP_LINEAR,
                    wrapS=pygltflib.REPEAT,
                    wrapT=pygltflib.REPEAT,
                )
            )
        if texture_uri is not None:
            gltf.images.append(pygltflib.Image(uri=texture_uri))
        gltf.set_binary_blob(gltf_binary_blob)
        return B3dmBody.from_gltf(gltf)

    @staticmethod
    def from_gltf(gltf: pygltflib.GLTF2) -> B3dmBody:
        # build tile body
        b = B3dmBody()
        b.gltf = gltf

        return b

    @staticmethod
    def from_array(b3dm_header: B3dmHeader, array: npt.NDArray[np.uint8]) -> B3dmBody:
        # build feature table
        ft_len = b3dm_header.ft_json_byte_length + b3dm_header.ft_bin_byte_length

        # build batch table
        bt_len = b3dm_header.bt_json_byte_length + b3dm_header.bt_bin_byte_length

        # build glTF
        gltf_len = (
            b3dm_header.tile_byte_length - ft_len - bt_len - B3dmHeader.BYTE_LENGTH
        )
        gltf_arr = array[ft_len + bt_len : ft_len + bt_len + gltf_len]
        gltf = pygltflib.GLTF2.load_from_bytes(b"".join(gltf_arr))

        # build tile body with batch table
        b = B3dmBody()
        b.gltf = gltf
        if ft_len > 0:
            b.feature_table = B3dmFeatureTable.from_array(b3dm_header, array[:ft_len])
        if bt_len > 0:
            batch_len = b.feature_table.get_batch_length()
            b.batch_table = BatchTable.from_array(
                b3dm_header, array[ft_len : ft_len + bt_len], batch_len
            )

        return b


def prepare_gltf_component(
    array_idx: int,
    array: npt.NDArray[np.uint8] | npt.NDArray[np.float32] | npt.NDArray[np.uint32],
    byte_offset: int,
    triangle_indices: bool = False,
) -> tuple[bytes, int, pygltflib.Accessor, pygltflib.BufferView]:
    array_blob = array.flatten().tobytes()
    additional_offset = len(array_blob)
    component_type = pygltflib.UNSIGNED_BYTE if triangle_indices else pygltflib.FLOAT
    if triangle_indices or array[0].size == 1:
        accessor_type = pygltflib.SCALAR
    else:
        accessor_type = pygltflib.VEC2 if array[0].size == 2 else pygltflib.VEC3
    BUFFER_INDEX = 0  # Everything is stored in the same buffer for sake of simplicity
    buffer_view_target = (
        pygltflib.ELEMENT_ARRAY_BUFFER if triangle_indices else pygltflib.ARRAY_BUFFER
    )
    accessor = pygltflib.Accessor(
        bufferView=array_idx,
        componentType=component_type,
        count=array.size if triangle_indices else len(array),
        type=accessor_type,
    )
    buffer_view = pygltflib.BufferView(
        buffer=BUFFER_INDEX,
        byteOffset=byte_offset,
        byteLength=additional_offset,
        target=buffer_view_target,
    )
    return array_blob, additional_offset, accessor, buffer_view
