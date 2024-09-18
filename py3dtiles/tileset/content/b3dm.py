from __future__ import annotations

import copy
import struct

import numpy as np
import numpy.typing as npt
import pygltflib

from py3dtiles.exceptions import InvalidB3dmError

from .b3dm_feature_table import B3dmFeatureTable
from .batch_table import BatchTable
from .gltf_utils import GltfPrimitive, gltf_component_from_primitive
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
        triangles: npt.NDArray[np.uint8] | None = None,
        batch_table: BatchTable | None = None,
        feature_table: B3dmFeatureTable | None = None,
        normal: npt.NDArray[np.float32] | None = None,
        uvs: npt.NDArray[np.float32] | None = None,
        batchids: npt.NDArray[np.uint32] | None = None,
        transform: npt.NDArray[np.float32] | None = None,
        texture_uri: str | None = None,
        material: pygltflib.Material | None = None,
    ) -> B3dm:
        """
        Creates a B3DM body from numpy arrays.

        :param points: array of vertex positions, must have a (n, 3) shape.
        :param triangles: array of triangle indices, must have a (n, 3) shape.
        :param batch_table: a batch table.
        :param feature_table: a feature table.
        :param normals: array of vertex normals, must have a (n, 3) shape.
        :param uvs: array of texture coordinates, must have a (n, 2) shape.
        :param batchids: array of batch table IDs, must have a (n) shape.
        :param texture_uri: the URI of the texture image if the primitive is textured.
        :param material: a glTF material. If not set, a default material is created.
        """
        return B3dm.from_primitives(
            [
                GltfPrimitive(
                    points,
                    triangles=triangles,
                    normals=normal,
                    uvs=uvs,
                    batchids=batchids,
                    texture_uri=texture_uri,
                    material=material,
                )
            ],
            batch_table,
            feature_table,
            transform,
        )

    @staticmethod
    def from_primitives(
        primitives: list[GltfPrimitive],
        batch_table: BatchTable | None = None,
        feature_table: B3dmFeatureTable | None = None,
        transform: npt.NDArray[np.float32] | None = None,
    ) -> B3dm:
        b3dm_header = B3dmHeader()
        b3dm_body = B3dmBody.from_primitives(primitives, transform)
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
    def from_primitives(
        primitives: list[GltfPrimitive],
        transform: npt.NDArray[np.float32] | None = None,
    ) -> B3dmBody:
        gltf_binary_blob = b""
        gltf_primitives = []
        gltf_accessors = []
        gltf_buffer_views = []
        counter = 0
        texture_index = 0

        node_matrix = np.identity(4).flatten("F").tolist()
        if transform is not None:
            node_matrix = transform.flatten("F").tolist()

        gltf = pygltflib.GLTF2(
            scene=0,
            scenes=[pygltflib.Scene(nodes=[0])],
            nodes=[pygltflib.Node(mesh=0, matrix=node_matrix)],
            meshes=[pygltflib.Mesh()],
        )

        for i, primitive in enumerate(primitives):
            (
                gltf_primitive,
                accessors,
                buffer_views,
                binary_blob,
            ) = gltf_component_from_primitive(
                primitive,
                len(gltf_binary_blob),
                counter,
            )

            material = (
                copy.deepcopy(primitive.material)
                if primitive.material is not None
                else pygltflib.Material(
                    pbrMetallicRoughness=pygltflib.PbrMetallicRoughness()
                )
            )
            if primitive.uvs is not None:
                gltf.textures.append(pygltflib.Texture(sampler=0, source=texture_index))
                material.pbrMetallicRoughness.baseColorTexture = pygltflib.TextureInfo(
                    index=texture_index
                )
                if primitive.texture_uri is None:
                    raise InvalidB3dmError(
                        "A texture URI must be specify if the glTF primitive has UV"
                    )
                gltf.images.append(pygltflib.Image(uri=primitive.texture_uri))
                texture_index += 1

            gltf.materials.append(material)
            gltf_primitive.material = i

            counter += len(accessors)
            gltf_primitives.append(gltf_primitive)
            gltf_accessors.extend(accessors)
            gltf_buffer_views.extend(buffer_views)
            gltf_binary_blob += binary_blob

        gltf.meshes[0].primitives = gltf_primitives
        gltf.accessors = gltf_accessors
        gltf.bufferViews = gltf_buffer_views
        gltf.buffers = [pygltflib.Buffer(byteLength=len(gltf_binary_blob))]
        if len(gltf.textures) > 0:
            gltf.samplers.append(
                pygltflib.Sampler(
                    magFilter=pygltflib.LINEAR,
                    minFilter=pygltflib.LINEAR_MIPMAP_LINEAR,
                    wrapS=pygltflib.REPEAT,
                    wrapT=pygltflib.REPEAT,
                )
            )

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
