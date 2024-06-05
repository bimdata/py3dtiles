from enum import Enum
import json
from typing import List

import numpy as np
import numpy.typing as npt

from py3dtiles.tileset.tile_content import TileContentHeader


class Feature:
    def __init__(self):
        self.positions = {}
        self.colors = {}
        # BIMDATA - ajout de dip
        self.dips = {}

    def to_array(self):
        pos_arr = np.array(
            [(self.positions["X"], self.positions["Y"], self.positions["Z"])]
        ).view(np.uint8)[0]

        if len(self.colors):
            col_arr = np.array(
                [(self.colors["Red"], self.colors["Green"], self.colors["Blue"])]
            ).view(np.uint8)[0]
        else:
            col_arr = np.array([])

        # BIMDATA - ajout de dip
        # Il sera nécéssaire de récupérer le type de données a intégrer en amont
        dips_array = np.array(
            np.dtype([("One", "u1"), ("Two", "u1"), ("Three", "u1")])
        ).view(np.uint8)[0]

        # BIMDATA * ajout de dips en output
        return [pos_arr, col_arr, dips_array]

    @staticmethod
    def from_values(x, y, z, red=None, green=None, blue=None):
        f = Feature()

        f.positions = {"X": x, "Y": y, "Z": z}

        if red or green or blue:
            f.colors = {"Red": red, "Green": green, "Blue": blue}
        else:
            f.colors = {}

        return f

    @staticmethod
    def from_array(
        positions_dtype,
        positions,
        colors_dtype=None,
        colors=None,
        dip_dtype=None,
        dips=None,
    ):
        """
        Parameters
        ----------
        positions_dtype : numpy.dtype

        positions : numpy.array
            Array of uint8.

        colors_dtype : numpy.dtype

        colors : numpy.array
            Array of uint8.

        Returns
        -------
        f : Feature
        """

        f = Feature()

        # extract positions
        f.positions = {}
        off = 0
        for d in positions_dtype.names:
            dt = positions_dtype[d]
            data = np.array(positions[off : off + dt.itemsize]).view(dt)[0]
            off += dt.itemsize
            f.positions[d] = data

        # extract colors
        f.colors = {}
        if colors_dtype is not None:
            off = 0
            for d in colors_dtype.names:
                dt = colors_dtype[d]
                data = np.array(colors[off : off + dt.itemsize]).view(dt)[0]
                off += dt.itemsize
                f.colors[d] = data

        # BIMDATA- ajout de ce bloc dip
        f.dips = {}
        off = 0
        for d in dip_dtype.names:
            dt = dip_dtype[d]
            data = np.array(dips[off : off + dt.itemsize]).view(dt)[0]
            off += dt.itemsize
            f.dips[d] = data

        return f


class SemanticPoint(Enum):
    # BIMDATA - a creuser
    NONE = 0
    POSITION = 1
    POSITION_QUANTIZED = 2
    RGBA = 3
    RGB = 4
    RGB565 = 5
    NORMAL = 6
    NORMAL_OCT16P = 7
    BATCH_ID = 8


class FeatureTableHeader:
    def __init__(self):
        # point semantics
        self.positions = SemanticPoint.POSITION
        self.positions_offset = 0
        self.positions_dtype = None

        self.colors = SemanticPoint.NONE
        self.colors_offset = 0
        self.colors_dtype = None

        self.normal = SemanticPoint.NONE
        self.normal_offset = 0
        self.normal_dtype = None

        # BIMDATA-- ajout de ce bloc dip
        self.dips = SemanticPoint.NONE
        self.dips_offset = 0
        self.dips_dtype = None

        # global semantics
        self.points_length = 0
        self.rtc = None

    def to_array(self):
        jsond = self.to_json()
        json_str = json.dumps(jsond).replace(" ", "")
        n = len(json_str) + 28
        if n % 8 != 0:
            json_str += " " * (8 - n % 8)
        return np.frombuffer(json_str.encode("utf-8"), dtype=np.uint8)

    def to_json(self):
        jsond = {}

        # length
        jsond["POINTS_LENGTH"] = self.points_length

        # rtc
        if self.rtc:
            jsond["RTC_CENTER"] = self.rtc

        # positions
        offset = {"byteOffset": self.positions_offset}
        if self.positions == SemanticPoint.POSITION:
            jsond["POSITION"] = offset
        elif self.positions == SemanticPoint.POSITION_QUANTIZED:
            jsond["POSITION_QUANTIZED"] = offset

        # colors
        offset = {"byteOffset": self.colors_offset}
        if self.colors == SemanticPoint.RGB:
            jsond["RGB"] = offset

        # BIMDATA-- permet de rajouter les données du dip dans le header du pnts
        offset = {"byteOffset": self.dips_offset}
        jsond["DIP"] = offset

        return jsond

    # BIMDATA- Rahout du dip_dtype en input
    @staticmethod
    def from_dtype(positions_dtype, colors_dtype, dips_dtype, nb_points):
        """
        Parameters
        ----------
        positions_dtype : numpy.dtype
            Numpy description of a positions.

        colors_dtype : numpy.dtype
            Numpy description of a colors.

        Returns
        -------
        fth : FeatureTableHeader
        """

        fth = FeatureTableHeader()
        fth.points_length = nb_points

        # search positions
        names = positions_dtype.names
        if ("X" in names) and ("Y" in names) and ("Z" in names):
            dtx = positions_dtype["X"]
            dty = positions_dtype["Y"]
            dtz = positions_dtype["Z"]
            fth.positions_offset = 0
            if dtx == np.float32 and dty == np.float32 and dtz == np.float32:
                fth.positions = SemanticPoint.POSITION
                fth.positions_dtype = np.dtype(
                    [("X", np.float32), ("Y", np.float32), ("Z", np.float32)]
                )
            elif dtx == np.uint16 and dty == np.uint16 and dtz == np.uint16:
                fth.positions = SemanticPoint.POSITION_QUANTIZED
                fth.positions_dtype = np.dtype(
                    [("X", np.uint16), ("Y", np.uint16), ("Z", np.uint16)]
                )

        # search colors
        if colors_dtype is not None and fth.positions_dtype:
            names = colors_dtype.names
            if ("Red" in names) and ("Green" in names) and ("Blue" in names):
                if "Alpha" in names:
                    fth.colors = SemanticPoint.RGBA
                    fth.colors_dtype = np.dtype(
                        [
                            ("Red", np.uint8),
                            ("Green", np.uint8),
                            ("Blue", np.uint8),
                            ("Alpha", np.uint8),
                        ]
                    )
                else:
                    fth.colors = SemanticPoint.RGB
                    fth.colors_dtype = np.dtype(
                        [("Red", np.uint8), ("Green", np.uint8), ("Blue", np.uint8)]
                    )

                fth.colors_offset = (
                    fth.positions_offset + nb_points * fth.positions_dtype.itemsize
                )

        else:
            fth.colors = SemanticPoint.NONE
            fth.colors_dtype = None

        # BIMDATA- Ajout des dip dans le pnts
        fth.dips = SemanticPoint.RGB
        fth.dips_dtype = np.dtype(
            [("One", np.uint8), ("Two", np.uint8), ("Three", np.uint8)]
        )
        # Adapter en fonction du format de la couleur / du nombre de sustom data / ...
        fth.dips_offset = fth.colors_offset + nb_points * fth.colors_dtype.itemsize

        return fth

    @staticmethod
    def from_array(array):
        """
        Parameters
        ----------
        array : numpy.array
            Json in 3D Tiles format. See py3dtiles/doc/semantics.json for an
            example.

        Returns
        -------
        fth : FeatureTableHeader
        """

        jsond = json.loads(array.tobytes().decode("utf-8"))
        fth = FeatureTableHeader()

        # search position
        if "POSITION" in jsond:
            fth.positions = SemanticPoint.POSITION
            fth.positions_offset = jsond["POSITION"]["byteOffset"]
            fth.positions_dtype = np.dtype(
                [("X", np.float32), ("Y", np.float32), ("Z", np.float32)]
            )
        elif "POSITION_QUANTIZED" in jsond:
            fth.positions = SemanticPoint.POSITION_QUANTIZED
            fth.positions_offset = jsond["POSITION_QUANTIZED"]["byteOffset"]
            fth.positions_dtype = np.dtype(
                [("X", np.uint16), ("Y", np.uint16), ("Z", np.uint16)]
            )
        else:
            fth.positions = SemanticPoint.NONE
            fth.positions_offset = 0
            fth.positions_dtype = None

        # search colors
        if "RGB" in jsond:
            fth.colors = SemanticPoint.RGB
            fth.colors_offset = jsond["RGB"]["byteOffset"]
            fth.colors_dtype = np.dtype(
                [("Red", np.uint8), ("Green", np.uint8), ("Blue", np.uint8)]
            )
        else:
            fth.colors = SemanticPoint.NONE
            fth.colors_offset = 0
            fth.colors_dtype = None

        # BIMDATA--- ajout des dips ici
        if "DIP" in jsond:
            fth.dips = SemanticPoint.RGB
            fth.dips_offset = jsond["DIP"]["byteOffset"]
            fth.dips_dtype = np.dtype(
                [("One", np.uint8), ("Two", np.uint8), ("Three", np.uint8)]
            )

        # points length
        if "POINTS_LENGTH" in jsond:
            fth.points_length = jsond["POINTS_LENGTH"]

        # RTC (Relative To Center)
        if "RTC_CENTER" in jsond:
            fth.rtc = jsond["RTC_CENTER"]
        else:
            fth.rtc = None

        return fth


class FeatureTableBody:
    def __init__(self):
        self.positions_arr = []
        self.positions_itemsize = 0

        self.colors_arr = []
        self.colors_itemsize = 0

        # BIMDATA- DIP
        self.dips_arr = []
        self.dips_itemsize = 0

    def to_array(self):
        arr = self.positions_arr
        if len(self.colors_arr):
            # BIMDATA- ajout des dip
            arr = np.concatenate((self.positions_arr, self.colors_arr, self.dips_arr))

        if len(arr) % 8 != 0:
            padding_str = " " * (8 - len(arr) % 8)
            arr = np.concatenate(
                (arr, np.frombuffer(padding_str.encode("utf-8"), dtype=np.uint8))
            )

        return arr

    @staticmethod
    def from_features(
        fth: FeatureTableHeader, features: List[Feature]
    ) -> "FeatureTableBody":
        b = FeatureTableBody()

        # extract positions
        if fth.positions_dtype is None:
            raise ValueError(
                "The FeatureTableHeader `fth` should have an initialized positions_dtype attribute."
            )
        b.positions_itemsize = fth.positions_dtype.itemsize
        b.positions_arr = np.array([], dtype=np.uint8)

        if fth.colors_dtype is not None:
            b.colors_itemsize = fth.colors_dtype.itemsize
            b.colors_arr = np.array([], dtype=np.uint8)

        # BIMDATA- extraction des données des dip
        b.dips_itemsize = fth.dips_dtype.itemsize
        b.dips_arr = np.array([], dtype=np.uint8)

        for f in features:
            fpos, fcol, fdip = f.to_array()
            b.positions_arr = np.concatenate((b.positions_arr, fpos))
            if fth.colors_dtype is not None:
                b.colors_arr = np.concatenate((b.colors_arr, fcol))

            # BIMDATA- ajout des dips
            b.dips_arr = np.concatenate((b.dips_arr, fdip))

        return b

    @staticmethod
    def from_array(fth, array):
        """
        Parameters
        ----------
        header : FeatureTableHeader

        array : numpy.array

        Returns
        -------
        ftb : FeatureTableBody
        """

        b = FeatureTableBody()

        nb_points = fth.points_length

        # extract positions
        pos_size = fth.positions_dtype.itemsize
        pos_offset = fth.positions_offset
        b.positions_arr = array[pos_offset : pos_offset + nb_points * pos_size]
        b.positions_itemsize = pos_size

        # extract colors
        if fth.colors != SemanticPoint.NONE:
            col_size = fth.colors_dtype.itemsize
            col_offset = fth.colors_offset
            b.colors_arr = array[col_offset : col_offset + col_size * nb_points]
            b.colors_itemsize = col_size

        # BIMDATA- ajout des dips
        if fth.dips != SemanticPoint.NONE:
            col_size = fth.dips_dtype.itemsize
            col_offset = fth.dips_offset
            b.dips_arr = array[col_offset : col_offset + col_size * nb_points]
            b.dips_itemsize = col_size

        return b

    def positions(self, n):
        itemsize = self.positions_itemsize
        return self.positions_arr[n * itemsize : (n + 1) * itemsize]

    def colors(self, n):
        if len(self.colors_arr):
            itemsize = self.colors_itemsize
            return self.colors_arr[n * itemsize : (n + 1) * itemsize]
        return []

    # BIMDATA- a voir si nécéssaire ?
    def dip(self, n):
        itemsize = self.dips_itemsize
        return self.dips_arr[n * itemsize : (n + 1) * itemsize]


class FeatureTable:
    def __init__(self):
        self.header = FeatureTableHeader()
        self.body = FeatureTableBody()

    def nb_points(self):
        return self.header.points_length

    def to_array(self):
        fth_arr = self.header.to_array()
        ftb_arr = self.body.to_array()
        return np.concatenate((fth_arr, ftb_arr))

    @staticmethod
    def from_array(th: TileContentHeader, array: np.ndarray) -> "FeatureTable":
        # build feature table header
        fth_len = th.ft_json_byte_length
        fth_arr = array[0:fth_len]
        fth = FeatureTableHeader.from_array(fth_arr)

        # build feature table body
        ftb_len = th.ft_bin_byte_length
        ftb_arr = array[fth_len : fth_len + ftb_len]
        ftb = FeatureTableBody.from_array(fth, ftb_arr)

        # build feature table
        ft = FeatureTable()
        ft.header = fth
        ft.body = ftb

        return ft

    @staticmethod
    def from_features(
        pd_type: npt.DTypeLike, cd_type: npt.DTypeLike, features: List[Feature]
    ) -> "FeatureTable":
        """
        pdtype : Numpy description for positions.
        cdtype : Numpy description for colors.
        """

        fth = FeatureTableHeader.from_dtype(pd_type, cd_type, len(features))
        ftb = FeatureTableBody.from_features(fth, features)

        ft = FeatureTable()
        ft.header = fth
        ft.body = ftb

        return ft

    def feature(self, n):
        # BIMDATA- ajout des dip - a voir si nécéssaire
        pos = self.body.positions(n)
        col = self.body.colors(n)
        dip = self.body.dip(n)
        return Feature.from_array(
            self.header.positions_dtype,
            pos,
            self.header.colors_dtype,
            col,
            self.header.dips_dtype,
            dip,
        )
