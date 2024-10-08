#!/usr/bin/env python3
import numpy
from plyfile import PlyData, PlyElement

# Code used to create the ply files in this folder
# with 8bits colors
vertex = numpy.array(
    [
        (0, 0, 0, 0, 128, 0),
        (0, 1, 1, 10, 0, 0),
        (1, 0, 1, 0, 0, 20),
        (1, 1, 0, 40, 40, 40),
    ],
    dtype=[
        ("x", "f4"),
        ("y", "f4"),
        ("z", "f4"),
        ("red", "u1"),
        ("green", "u1"),
        ("blue", "u1"),
    ],
)
el = PlyElement.describe(vertex, "vertex")
PlyData([el]).write("simple_with_8_bits_colors.ply")

# with 16 bits colors
vertex = numpy.array(
    [
        (0, 0, 0, 0, 128, 0),
        (0, 1, 1, 256, 0, 0),
        (1, 0, 1, 0, 0, 1024),
        (1, 1, 0, 65535, 65535, 65535),
    ],
    dtype=[
        ("x", "f4"),
        ("y", "f4"),
        ("z", "f4"),
        ("red", "u2"),
        ("green", "u2"),
        ("blue", "u2"),
    ],
)
el = PlyElement.describe(vertex, "vertex")
PlyData([el]).write("simple_with_16_bits_colors.ply")

# with classification
vertex = numpy.array(
    [
        (0, 0, 0, 0, 128, 0, 1),
        (0, 1, 1, 256, 0, 0, 1),
        (1, 0, 1, 0, 0, 1024, 2),
        (1, 1, 0, 65535, 65535, 65535, 2),
    ],
    dtype=[
        ("x", "f4"),
        ("y", "f4"),
        ("z", "f4"),
        ("red", "u2"),
        ("green", "u2"),
        ("blue", "u2"),
        ("classification", "u1"),
    ],
)
el = PlyElement.describe(vertex, "vertex")
PlyData([el]).write("simple_with_classification.ply")

# with intensity
vertex = numpy.array(
    [
        (0, 0, 0, 0, 128, 0, 80),
        (0, 1, 1, 256, 0, 0, 90),
        (1, 0, 1, 0, 0, 1024, 15),
        (1, 1, 0, 65535, 65535, 65535, 129),
    ],
    dtype=[
        ("x", "f4"),
        ("y", "f4"),
        ("z", "f4"),
        ("red", "u2"),
        ("green", "u2"),
        ("blue", "u2"),
        ("intensity", "u1"),
    ],
)
el = PlyElement.describe(vertex, "vertex")
PlyData([el]).write("simple_with_intensity.ply")

# with classification AND intensity
vertex = numpy.array(
    [
        (0, 0, 0, 0, 128, 0, 1, 80),
        (0, 1, 1, 256, 0, 0, 1, 90),
        (1, 0, 1, 0, 0, 1024, 2, 15),
        (1, 1, 0, 65535, 65535, 65535, 2, 129),
    ],
    dtype=[
        ("x", "f4"),
        ("y", "f4"),
        ("z", "f4"),
        ("red", "u2"),
        ("green", "u2"),
        ("blue", "u2"),
        ("classification", "u1"),
        ("intensity", "u1"),
    ],
)
el = PlyElement.describe(vertex, "vertex")
PlyData([el]).write("simple_with_classification_and_intensity.ply")

# with classification AND intensity as f4
vertex = numpy.array(
    [
        (0, 0, 0, 0, 128, 0, 1, 80.1),
        (0, 1, 1, 256, 0, 0, 1, 90.4),
        (1, 0, 1, 0, 0, 1024, 2, -15),
        (1, 1, 0, 65535, 65535, 65535, 2, -129.0),
    ],
    dtype=[
        ("x", "f4"),
        ("y", "f4"),
        ("z", "f4"),
        ("red", "u2"),
        ("green", "u2"),
        ("blue", "u2"),
        ("classification", "u1"),
        ("intensity", "f4"),
    ],
)
el = PlyElement.describe(vertex, "vertex")
PlyData([el]).write("simple_with_classification_and_intensity_f4.ply")
