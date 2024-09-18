from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import numpy.typing as npt
from pyproj import Transformer

from py3dtiles.tilers.base_tiler import SharedMetadata


@dataclass(frozen=True)
class PointSharedMetadata(SharedMetadata):
    transformer: Optional[Transformer]
    root_aabb: npt.NDArray[np.float64]
    root_spacing: float
    scale: npt.NDArray[np.float32]
    out_folder: Path
    write_rgb: bool
    color_scale: Optional[float]
    write_classification: bool
    write_intensity: bool
    verbosity: int
