import unittest
from filecmp import cmp
from pathlib import Path

import numpy as np

from py3dtiles.tilers.b3dm.wkb_utils import TriangleSoup
from py3dtiles.tileset.content import B3dm, B3dmHeader, read_binary_tile_content
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
        expected_gltf_json_chunk_len = 1212
        expected_gltf_bin_chunk_len = 4976
        self.assertEqual(
            tile_content.header.tile_byte_length,
            expected_tile_header_len
            + expected_feature_table_header_len
            + expected_feature_table_body_len
            + expected_batch_table_header_len
            + expected_batch_table_body_len
            + expected_gltf_header_len
            + expected_gltf_json_chunk_len
            + expected_gltf_bin_chunk_len,
        )
        self.assertEqual(
            tile_content.header.ft_json_byte_length, expected_feature_table_header_len
        )
        self.assertEqual(
            tile_content.header.ft_bin_byte_length, expected_feature_table_body_len
        )
        self.assertEqual(
            tile_content.header.bt_json_byte_length, expected_batch_table_header_len
        )
        self.assertEqual(
            tile_content.header.bt_bin_byte_length, expected_batch_table_body_len
        )
        self.assertDictEqual(
            tile_content.body.batch_table.header.data,
            {"id": ["BATIMENT0000000240853073", "BATIMENT0000000240853157"]},
        )
        self.assertEqual(tile_content.body.feature_table.get_batch_length(), 2)
        # self.assertEqual(len(b"".join(tile_content.body.gltf.save_to_bytes())), 6040)
        self.assertEqual(tile_content.body.gltf.asset.version, "2.0")

        path_name = Path("tests/output_tests/buildings.b3dm")
        path_name.parent.mkdir(parents=True, exist_ok=True)
        tile_content.save_as(path_name)
        self.assertTrue(cmp("tests/fixtures/buildings.b3dm", path_name))


class TestTileContentBuilder(unittest.TestCase):
    def test_build(self) -> None:
        with open("tests/fixtures/building.wkb", "rb") as f:
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
        expected_gltf_json_chunk_len = 860
        expected_gltf_bin_chunk_len = 1112
        self.assertEqual(
            t.header.ft_json_byte_length, expected_feature_table_header_len
        )
        self.assertEqual(t.header.ft_bin_byte_length, expected_feature_table_body_len)
        self.assertEqual(t.header.bt_json_byte_length, expected_batch_table_header_len)
        self.assertEqual(t.header.bt_bin_byte_length, expected_batch_table_body_len)
        self.assertEqual(
            t.header.tile_byte_length,
            expected_tile_header_len
            + expected_feature_table_header_len
            + expected_feature_table_body_len
            + expected_batch_table_header_len
            + expected_batch_table_body_len
            + expected_gltf_header_len
            + expected_gltf_json_chunk_len
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

        # gltf = GlTF.from_binary_arrays(
        #     arrays, transform, texture_uri="squaretexture.jpg"
        # )
        t = B3dm.from_numpy_arrays(
            ts.vertices,
            ts.triangle_indices,
            normal=ts.compute_normals(),
            # uvs=ts.get_data(0),  # TODO: support UV data in GlTF
        )

        # get an array
        t.to_array()
        self.assertEqual(t.header.version, 1.0)
        # self.assertEqual(t.header.tile_byte_length, 1556)
        self.assertEqual(t.header.ft_json_byte_length, 0)
        self.assertEqual(t.header.ft_bin_byte_length, 0)
        self.assertEqual(t.header.bt_json_byte_length, 0)
        self.assertEqual(t.header.bt_bin_byte_length, 0)

        # t.save_as("/tmp/py3dtiles_test_build_1.b3dm")

    def test_build_and_read_gltf_content(self) -> None:
        """See "Create a mesh, convert to bytes, convert back to mesh" section from
        https://gitlab.com/dodgyville/pygltflib/. This test is an adaptation of the pygltflib
        documentation.

        """
        with open("tests/fixtures/building.wkb", "rb") as f:
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
        ).reshape((-1, 3))
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
            count=points_accessor.count,
        ).reshape((-1, 3))
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
            count=normals_accessor.count,
        ).reshape((-1, 3))
        np.testing.assert_array_equal(normals, ts.compute_normals())
