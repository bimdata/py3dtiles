import struct
import unittest
from filecmp import cmp
from pathlib import Path

import numpy as np
import pygltflib

from py3dtiles.exceptions import InvalidB3dmError
from py3dtiles.tilers.b3dm.wkb_utils import TriangleSoup
from py3dtiles.tileset.content import (
    B3dm,
    B3dmHeader,
    GltfAttribute,
    GltfPrimitive,
    read_binary_tile_content,
)
from py3dtiles.tileset.content.b3dm_feature_table import B3dmFeatureTable


class TestTileContentReader(unittest.TestCase):
    def test_read_and_write(self) -> None:
        tile_content = read_binary_tile_content(Path("tests/fixtures/buildings.b3dm"))
        if not isinstance(tile_content, B3dm):
            raise ValueError(
                f"The file 'tests/fixtures/buildings.b3dm' is a b3dm, not a {type(tile_content)}"
            )

        expected_tile_header_len = 28
        expected_feature_table_header_len = 20
        expected_feature_table_body_len = 0
        expected_batch_table_header_len = 64
        expected_batch_table_body_len = 0
        expected_gltf_header_len = 12  # magic + version + length
        expected_gltf_chunk_len = 8  # chunk length + chunk magic (JSON/BIN)
        expected_gltf_json_chunk_len = 1220
        expected_gltf_bin_chunk_len = 4968
        # Test feature table length
        self.assertEqual(
            tile_content.header.ft_json_byte_length, expected_feature_table_header_len
        )
        self.assertEqual(
            tile_content.header.ft_bin_byte_length, expected_feature_table_body_len
        )
        # Test batch table length
        self.assertEqual(
            tile_content.header.bt_json_byte_length, expected_batch_table_header_len
        )
        self.assertEqual(
            tile_content.header.bt_bin_byte_length, expected_batch_table_body_len
        )
        # Test gltf length
        (
            _,
            _,
            length,
            json_blob_length,
            _,
            json_blob,
            bin_blob_length,
            _,
            bin_blob,
        ) = tile_content.body.gltf.save_to_bytes()
        self.assertEqual(
            struct.unpack("<I", json_blob_length)[0], expected_gltf_json_chunk_len
        )
        self.assertEqual(len(json_blob), expected_gltf_json_chunk_len)
        self.assertEqual(
            struct.unpack("<I", bin_blob_length)[0], expected_gltf_bin_chunk_len
        )
        self.assertEqual(len(bin_blob), expected_gltf_bin_chunk_len)
        # Test total length
        self.assertEqual(
            tile_content.header.tile_byte_length,
            expected_tile_header_len
            + expected_feature_table_header_len
            + expected_feature_table_body_len
            + expected_batch_table_header_len
            + expected_batch_table_body_len
            + expected_gltf_header_len
            + expected_gltf_chunk_len
            + expected_gltf_json_chunk_len
            + expected_gltf_chunk_len
            + expected_gltf_bin_chunk_len,
        )
        self.assertDictEqual(
            tile_content.body.batch_table.header.data,
            {"id": ["BATIMENT0000000240853073", "BATIMENT0000000240853157"]},
        )
        self.assertEqual(tile_content.body.feature_table.get_batch_length(), 2)
        self.assertEqual(tile_content.body.gltf.asset.version, "2.0")
        self.assertEqual(len(b"".join(tile_content.body.gltf.save_to_bytes())), 6216)

        path_name = Path("tests/output_tests/buildings.b3dm")
        path_name.parent.mkdir(parents=True, exist_ok=True)
        tile_content.save_as(path_name)
        self.assertTrue(cmp("tests/fixtures/buildings.b3dm", path_name))

    def test_str(self) -> None:
        tile_content = read_binary_tile_content(Path("tests/fixtures/buildings.b3dm"))
        expected_string_components = [
            "------ Tile header ------",
            "magic: b'b3dm'",
            "version: 1",
            "tile_byte_length: 6328",
            "json_feature_table_length: 20",
            "bin_feature_table_length: 0",
            "json_batch_table_length: 64",
            "bin_batch_table_length: 0",
            "------ Tile body ------",
            "feature_table_batch_length: 2",
            "gltf_magic: b'glTF'",
            "gltf_version: 2.0",
            "gltf_length: 6216",
            "gltf_json_chunk_length: 1220",
            "gltf_bin_chunk_length: 4968",
        ]
        string_components = str(tile_content).split("\n")
        for expected_line, line in zip(expected_string_components, string_components):
            assert expected_line == line


class TestTileContentBuilder(unittest.TestCase):
    def test_build(self) -> None:
        with open("tests/fixtures/building/building.wkb", "rb") as f:
            wkb = f.read()
        ts = TriangleSoup.from_wkb_multipolygon(wkb)

        # translation : 1842015.125, 5177109.25, 247.87364196777344
        transform = np.array(
            [
                [1, 0, 0, 1842015.125],
                [0, 1, 0, 5177109.25],
                [0, 0, 1, 247.87364196777344],
                [0, 0, 0, 1],
            ],
            dtype=float,
        )
        feature_table = B3dmFeatureTable()
        feature_table.set_batch_length(1)
        t = B3dm.from_numpy_arrays(
            ts.vertices,
            ts.triangle_indices,
            feature_table=feature_table,
            normal=ts.compute_normals(),
            transform=transform,
        )

        # get an array
        t.to_array()
        self.assertEqual(t.header.version, 1.0)

        # Test the tile byte length
        expected_tile_header_len = 28
        expected_feature_table_header_len = 20
        expected_feature_table_body_len = 0
        expected_batch_table_header_len = 0
        expected_batch_table_body_len = 0
        expected_gltf_header_len = 12  # magic + version + length
        expected_gltf_chunk_len = 8  # chunk length + chunk magic (JSON/BIN)
        expected_gltf_json_chunk_len = 1204
        expected_gltf_bin_chunk_len = 1104
        # Test feature table length
        self.assertEqual(
            t.header.ft_json_byte_length, expected_feature_table_header_len
        )
        self.assertEqual(t.header.ft_bin_byte_length, expected_feature_table_body_len)
        # Test batch table length
        self.assertEqual(t.header.bt_json_byte_length, expected_batch_table_header_len)
        self.assertEqual(t.header.bt_bin_byte_length, expected_batch_table_body_len)
        # Test gltf length
        (
            _,
            _,
            length,
            json_blob_length,
            _,
            json_blob,
            bin_blob_length,
            _,
            bin_blob,
        ) = t.body.gltf.save_to_bytes()
        self.assertEqual(
            struct.unpack("<I", json_blob_length)[0], expected_gltf_json_chunk_len
        )
        self.assertEqual(len(json_blob), expected_gltf_json_chunk_len)
        self.assertEqual(
            struct.unpack("<I", bin_blob_length)[0], expected_gltf_bin_chunk_len
        )
        self.assertEqual(len(bin_blob), expected_gltf_bin_chunk_len)
        # Test total length
        self.assertEqual(
            t.header.tile_byte_length,
            expected_tile_header_len
            + expected_feature_table_header_len
            + expected_feature_table_body_len
            + expected_batch_table_header_len
            + expected_batch_table_body_len
            + expected_gltf_header_len
            + expected_gltf_chunk_len
            + expected_gltf_json_chunk_len
            + expected_gltf_chunk_len
            + expected_gltf_bin_chunk_len,
        )
        self.assertEqual(
            t.header.tile_byte_length % 8, 0
        )  # tile bytes must be 8-byte aligned

        # Test the feature table byte lengths
        json_feature_table_end = B3dmHeader.BYTE_LENGTH + t.header.ft_json_byte_length
        self.assertEqual(json_feature_table_end % 8, 0)

        # This 20 corresponds to the length of the JSON feature table ("{'BATCH_LENGTH':1}") + the padding to align on 8-bytes
        self.assertEqual(t.header.ft_json_byte_length, 20)

        bin_feature_table_end = json_feature_table_end + t.header.ft_bin_byte_length
        self.assertEqual(bin_feature_table_end % 8, 0)
        self.assertEqual(t.header.ft_bin_byte_length, 0)

        # Test the batch table byte lengths
        self.assertEqual(t.header.bt_json_byte_length, 0)
        self.assertEqual(t.header.bt_bin_byte_length, 0)

        # Test the gltf byte length
        gltf_start_bounding = (
            bin_feature_table_end
            + t.header.bt_json_byte_length
            + t.header.bt_bin_byte_length
        )
        self.assertEqual(
            gltf_start_bounding % 8, 0
        )  # the gltf part must be 8-byte aligned
        self.assertEqual(
            len(b"".join(t.body.gltf.save_to_bytes())) % 8, 0
        )  # gltf bytes must be 8-byte aligned

        # t.save_as("/tmp/py3dtiles_test_build_1.b3dm")


class TestTexturedTileBuilder(unittest.TestCase):
    def test_build(self) -> None:
        with open("tests/fixtures/square.wkb", "rb") as f:
            wkb = f.read()
        with open("tests/fixtures/squareUV.wkb", "rb") as f:
            wkbuv = f.read()
        ts = TriangleSoup.from_wkb_multipolygon(wkb, [wkbuv])

        t = B3dm.from_numpy_arrays(
            ts.vertices,
            ts.triangle_indices,
            normal=ts.compute_normals(),
            uvs=ts.get_data(0),
            texture_uri="tests/fixtures/squaretexture.jpg",
        )

        # get an array
        t.to_array()
        self.assertEqual(t.header.version, 1.0)
        self.assertEqual(t.header.tile_byte_length, 1692)
        self.assertEqual(t.header.ft_json_byte_length, 0)
        self.assertEqual(t.header.ft_bin_byte_length, 0)
        self.assertEqual(t.header.bt_json_byte_length, 0)
        self.assertEqual(t.header.bt_bin_byte_length, 0)
        accessors = t.body.gltf.accessors
        self.assertEqual(accessors[1].min, [0, 0, 0])
        self.assertEqual(accessors[1].max, [10, 10, 0])

        t_without_normals = B3dm.from_numpy_arrays(
            ts.vertices,
            ts.triangle_indices,
            uvs=ts.get_data(0),
            texture_uri="tests/fixtures/squaretexture.jpg",
        )

        # get an array
        t_without_normals.to_array()
        self.assertEqual(t_without_normals.header.tile_byte_length, 1452)

        # t.save_as("/tmp/py3dtiles_test_build_1.b3dm")

    def test_build_batchids(self) -> None:
        with open("tests/fixtures/square.wkb", "rb") as f:
            wkb = f.read()
        ts = TriangleSoup.from_wkb_multipolygon(wkb)
        ft = B3dmFeatureTable()
        ft.set_batch_length(2)

        t = B3dm.from_numpy_arrays(
            ts.vertices,
            ts.triangle_indices,
            feature_table=ft,
            normal=np.array(
                [
                    [0.0, 0.0, -1.0],
                    [0.0, 0.0, -1.0],
                    [0.0, 0.0, -1.0],
                    [-0.0, -0.0, -1.0],
                    [-0.0, -0.0, -1.0],
                    [-0.0, -0.0, -1.0],
                ],
                dtype=np.float32,
            ),
            batchids=np.array([0, 0, 0, 1, 1, 1], dtype=np.uint32),
        )

        # get an array
        t.to_array()
        self.assertEqual(t.header.version, 1.0)
        self.assertEqual(t.header.tile_byte_length, 1480)
        self.assertEqual(t.header.ft_json_byte_length, 20)
        self.assertEqual(t.header.ft_bin_byte_length, 0)
        self.assertEqual(t.header.bt_json_byte_length, 0)
        self.assertEqual(t.header.bt_bin_byte_length, 0)

    def test_build_multiple_parts(self) -> None:
        with open("tests/fixtures/square.wkb", "rb") as f:
            wkb = f.read()
        with open("tests/fixtures/squareUV.wkb", "rb") as f:
            wkbuv = f.read()
        ts_0 = TriangleSoup.from_wkb_multipolygon(wkb)
        ts_1 = TriangleSoup.from_wkb_multipolygon(wkb, [wkbuv])
        for triangle in ts_1.triangles[0]:
            for point in triangle:
                point[1] += 30
        ts_2 = TriangleSoup.from_wkb_multipolygon(wkb)
        for triangle in ts_2.triangles[0]:
            for point in triangle:
                point[1] -= 30
        ts_3 = TriangleSoup.from_wkb_multipolygon(wkb)
        for triangle in ts_3.triangles[0]:
            for point in triangle:
                point[1] += 60
        ts_4 = TriangleSoup.from_wkb_multipolygon(wkb, [wkbuv])
        for triangle in ts_4.triangles[0]:
            for point in triangle:
                point[1] += 90
        vertex_color = GltfAttribute(
            "COLOR_0",
            pygltflib.VEC3,
            pygltflib.FLOAT,
            np.array(
                [
                    [0, 0, 1],
                    [1, 0, 0],
                    [0, 1, 0],
                    [1, 0, 0],
                    [0, 1, 0],
                    [0, 0, 1],
                ],
                dtype=np.float32,
            ),
        )
        material = pygltflib.Material(
            pbrMetallicRoughness=pygltflib.PbrMetallicRoughness(
                baseColorFactor=[1.0, 0.0, 0.0, 0.75],
                metallicFactor=0.5,
                roughnessFactor=0.5,
            )
        )
        ft = B3dmFeatureTable()
        ft.set_batch_length(0)
        primitives = [
            GltfPrimitive(ts_0.vertices, ts_0.triangle_indices, ts_0.compute_normals()),
            GltfPrimitive(
                ts_1.vertices,
                ts_1.triangle_indices,
                ts_1.compute_normals(),
                ts_1.get_data(0),
                texture_uri="squaretexture.jpg",
            ),
            GltfPrimitive(
                ts_2.vertices,
                ts_2.triangle_indices,
                ts_2.compute_normals(),
                additional_attributes=[vertex_color],
            ),
            GltfPrimitive(
                ts_3.vertices,
                ts_3.triangle_indices,
                ts_3.compute_normals(),
                material=material,
            ),
            GltfPrimitive(
                np.array(ts_4.triangles[0]).flatten().reshape((-1, 3)),
                normals=ts_4.compute_normals(),
                uvs=ts_4.get_data(0),
                texture_uri="squaretexture.jpg",
                material=material,
            ),
        ]

        t = B3dm.from_primitives(
            primitives,
            feature_table=ft,
        )

        # get an array
        t.to_array()
        self.assertEqual(t.header.version, 1.0)
        self.assertEqual(t.header.tile_byte_length, 5776)
        self.assertEqual(t.header.ft_json_byte_length, 20)
        self.assertEqual(t.header.ft_bin_byte_length, 0)
        self.assertEqual(t.header.bt_json_byte_length, 0)
        self.assertEqual(t.header.bt_bin_byte_length, 0)
        accessors = t.body.gltf.accessors
        gltf_primitives = t.body.gltf.meshes[0].primitives
        self.assertEqual(accessors[1].min, [0, 0, 0])
        self.assertEqual(accessors[1].max, [10, 10, 0])
        self.assertEqual(len(accessors), 17)
        self.assertEqual(len(gltf_primitives), 5)
        self.assertEqual(gltf_primitives[2].attributes.COLOR_0, 10)
        self.assertEqual(
            t.body.gltf.materials[3].pbrMetallicRoughness.baseColorFactor,
            [1.0, 0.0, 0.0, 0.75],
        )
        with self.assertRaises(
            InvalidB3dmError
        ):  # Assert an error is raised if a GltfPrimitive as UVs but no texture URI
            _ = B3dm.from_primitives(
                [
                    GltfPrimitive(
                        ts_1.vertices,
                        ts_1.triangle_indices,
                        uvs=ts_1.get_data(0),
                        material=material,
                    ),
                ]
            )

    def test_build_and_read_gltf_content(self) -> None:
        """See "Create a mesh, convert to bytes, convert back to mesh" section from
        https://gitlab.com/dodgyville/pygltflib/. This test is an adaptation of the pygltflib
        documentation.

        """
        with open("tests/fixtures/building/building.wkb", "rb") as f:
            wkb = f.read()
        ts = TriangleSoup.from_wkb_multipolygon(wkb)
        t = B3dm.from_numpy_arrays(
            ts.vertices,
            ts.triangle_indices,
            normal=ts.compute_normals(),
        )

        gltf = t.body.gltf
        gltf_binary_blob = gltf.binary_blob()

        triangles_accessor = gltf.accessors[gltf.meshes[0].primitives[0].indices]
        triangles_buffer_view = gltf.bufferViews[triangles_accessor.bufferView]
        triangles = np.frombuffer(
            gltf_binary_blob[
                triangles_buffer_view.byteOffset
                + triangles_accessor.byteOffset : triangles_buffer_view.byteOffset
                + triangles_buffer_view.byteLength
            ],
            dtype="uint8",
            count=triangles_accessor.count,
        ).reshape(int(triangles_accessor.count / 3), 3)
        np.testing.assert_array_equal(triangles, ts.triangle_indices)

        points_accessor = gltf.accessors[
            gltf.meshes[0].primitives[0].attributes.POSITION
        ]
        points_buffer_view = gltf.bufferViews[points_accessor.bufferView]
        points = np.frombuffer(
            gltf_binary_blob[
                points_buffer_view.byteOffset
                + points_accessor.byteOffset : points_buffer_view.byteOffset
                + points_buffer_view.byteLength
            ],
            dtype="float32",
            count=points_accessor.count * 3,
        ).reshape(points_accessor.count, 3)
        np.testing.assert_array_equal(points, ts.vertices)

        normals_accessor = gltf.accessors[
            gltf.meshes[0].primitives[0].attributes.NORMAL
        ]
        normals_buffer_view = gltf.bufferViews[normals_accessor.bufferView]
        normals = np.frombuffer(
            gltf_binary_blob[
                normals_buffer_view.byteOffset
                + normals_accessor.byteOffset : normals_buffer_view.byteOffset
                + normals_buffer_view.byteLength
            ],
            dtype="float32",
            count=normals_accessor.count * 3,
        ).reshape(normals_accessor.count, 3)
        np.testing.assert_array_equal(normals, ts.compute_normals())
