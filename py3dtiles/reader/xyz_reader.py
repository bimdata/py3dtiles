import csv
import math
from pathlib import Path
from typing import Generator, List, Optional, Tuple

import numpy as np
import numpy.typing as npt
from pyproj import Transformer

from py3dtiles.typing import MetadataReaderType, OffsetScaleType, PortionItemType


def get_metadata(path: Path, fraction: int = 100) -> MetadataReaderType:
    aabb = None
    count = 0
    seek_values = []

    with path.open() as f:
        file_sample = f.read(
            2048
        )  # For performance reasons we just snif the first part
        dialect = csv.Sniffer().sniff(file_sample)

        f.seek(0)
        if csv.Sniffer().has_header(file_sample):
            f.readline()

        while True:
            batch = 10_000
            points = np.zeros((batch, 3))

            offset = f.tell()
            for i in range(batch):
                line = f.readline()
                if not line:
                    points = np.resize(points, (i, 3))
                    break
                points[i] = [float(s) for s in line.split(dialect.delimiter)][:3]

            if points.shape[0] == 0:
                break

            if not count % 1_000_000:
                seek_values += [offset]

            count += points.shape[0]
            batch_aabb = np.array([np.min(points, axis=0), np.max(points, axis=0)])

            # Update aabb
            if aabb is None:
                aabb = batch_aabb
            else:
                aabb[0] = np.minimum(aabb[0], batch_aabb[0])
                aabb[1] = np.maximum(aabb[1], batch_aabb[1])

        # We need an exact point count
        point_count = count * fraction // 100

        _1M = min(count, 1_000_000)
        steps = math.ceil(count / _1M)
        if steps != len(seek_values):
            raise ValueError(
                "the size of seek_values should be equal to steps,"
                f"currently steps = {steps} and len(seek_values) = {len(seek_values)}"
            )
        portions: List[PortionItemType] = [
            (i * _1M, min(count, (i + 1) * _1M), seek_values[i]) for i in range(steps)
        ]

        pointcloud_file_portions = [(str(path), p) for p in portions]

    if aabb is None:
        raise ValueError(f"There is no point in the file {path}")

    return {
        "portions": pointcloud_file_portions,
        "aabb": aabb,
        "crs_in": None,
        "point_count": point_count,
        "avg_min": aabb[0],
    }


def run(
    filename: str,
    offset_scale: OffsetScaleType,
    portion: PortionItemType,
    transformer: Optional[Transformer],
    color_scale: Optional[float],
    write_intensity: bool,
) -> Generator[
    Tuple[
        npt.NDArray[np.float32],
        npt.NDArray[np.uint8],
        npt.NDArray[np.uint8],
        npt.NDArray[np.uint8],
    ],
    None,
    None,
]:
    """
    Reads points from a .xyz or .csv file

    Consider XYZIRGB format following FME documentation(*). We do the
    following hypothesis and enhancements:

    - A header line defining columns in CSV style may be present, but will be ignored.
    - The separator separating the columns is automagically guessed by the
      reader. This is generally fail safe. It will not harm to use commonly
      accepted separators like space, tab, colon, semi-colon.
    - The order of columns is fixed. The reader does the following assumptions:
      - 3 columns mean XYZ
      - 4 columns mean XYZI
      - 6 columns mean XYZRGB
      - 7 columns mean XYZIRGB
      - 8 columns mean XYZIRGB followed by classification data. Classification data must be integers only.
      - all columns after the 8th column will be ignored.

    NOTE: we assume RGB are 8 bits components.

    (*) See: https://docs.safe.com/fme/html/FME_Desktop_Documentation/FME_ReadersWriters/pointcloudxyz/pointcloudxyz.htm
    """
    with open(filename) as f:

        dialect = csv.Sniffer().sniff(f.read(2048))
        f.seek(0)
        f.readline()  # skip first line in case there is a header we promised to ignore
        feature_nb = len(f.readline().split(dialect.delimiter))
        if feature_nb < 8:
            feature_nb = 7  # we pad to 7 columns with 0
        if feature_nb > 8:
            feature_nb = 8  # We ignore other data as downstream only 1 value for classification data is supported.
            # Once downstream supports multiple classification values this reader will as well
            # when this line is removed.

        point_count = portion[1] - portion[0]

        step = min(point_count, max((point_count) // 10, 100000))

        f.seek(portion[2])

        for _ in range(0, point_count, step):
            points = np.zeros((step, feature_nb), dtype=np.float32)

            for j in range(step):
                line = f.readline()
                if not line:
                    points = np.resize(points, (j, feature_nb))
                    break
                line_features: List[Optional[float]] = [
                    float(s) for s in line.split(dialect.delimiter)[:feature_nb]
                ]
                if len(line_features) == 3:
                    line_features += [None] * 4  # Insert intensity and RGB
                elif len(line_features) == 4:
                    line_features += [None] * 3  # Insert RGB
                elif len(line_features) == 6:
                    line_features.insert(3, None)  # Insert intensity
                points[j] = line_features

            x, y, z = (points[:, c] for c in [0, 1, 2])

            if transformer:
                x, y, z = transformer.transform(x, y, z)

            x = (x + offset_scale[0][0]) * offset_scale[1][0]
            y = (y + offset_scale[0][1]) * offset_scale[1][1]
            z = (z + offset_scale[0][2]) * offset_scale[1][2]

            coords = np.vstack((x, y, z)).transpose()

            if offset_scale[2] is not None:
                # Apply transformation matrix (because the tile's transform will contain
                # the inverse of this matrix)
                coords = np.dot(coords, offset_scale[2])

            coords = np.ascontiguousarray(coords.astype(np.float32))

            # Read colors: 3 last columns when excluding classification data
            if color_scale is None:
                colors = points[:, 4:7].astype(np.uint8)
            else:
                colors = np.clip(points[:, 4:7] * color_scale, 0, 255).astype(np.uint8)

            if feature_nb > 7:  # we have classification data
                classification = np.array(points[:, 7:], dtype=np.uint8).reshape(-1, 1)
            else:
                classification = np.zeros((points.shape[0], 1), dtype=np.uint8)

            if feature_nb in (4, 7, 8) and write_intensity:
                intensity = np.array(points[:, 3], dtype=np.uint8).reshape(-1, 1)
            else:
                intensity = np.zeros((points.shape[0], 1), dtype=np.uint8)

            yield coords, colors, classification, intensity
