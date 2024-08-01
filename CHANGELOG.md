# Changelog

All notable changes to this project will be documented in this file.

## v8.0.2 (2024-08-01)

Changes for this release are only about our CI pipeline.

We fixed the bug with the tag name for the docker image: it was v8-0-1 in the previous release instead of v8.0.1.

## v8.0.1 (2024-07-24)

### fix

- revert commit 395f294ed2cd38125ed132fdc13289e2870aa6d0 that breaks the process launching on windows

## v8.0.0 (2024-07-16)

### BREAKING CHANGE

- The `fraction` parameter  of `convert` (and the `--fraction` cli flag) has been removed, because we didn't actually use it in the code
- The . folder by default is now /data on docker image, please update your mounts accordingly.
- We replaced the home-made gltf support by pygltflib. It should be compatible with the previous usage for the most part, except for direct usage of `gltf.py` (replace it with direct usage of pygltflib) and `B3dm.from_numpy_arrays`, which has been replaced by `B3dm.from_primitives`. We believe this will be vastly easier to use. Under the hood, it generates gltf primitives inside the tile.
- the `all` section in setup.py has been removed because `pyproject.toml` doesn't support creating them from all the other sections, please use `pip install -e .[postgres,las,ply]` instead.
- TileContent.print_info(), B3dm.print_info() and Pnts.print_info() have been removed and replaced by __str__ methods. By assuming `b3dm_tile` is a B3dm tile, one may access to string representations with print(b3dm_tile) or str(b3dm_tile).
- `Tileset.root_uri` must now be set after the construction
- `BoundingVolume`: the functions `is_box`, `is_region` and `is_sphere` from this class are removed, use `isinstance(BoundingVolumeBox)` (or the relevant subclass) instead.


### Feat

- the docker image is now also [pushed on dockerhub](https://hub.docker.com/r/py3dtiles/py3dtiles)
- the home-made gltf support is replaced by pygltflib. a `gltf_utils` module has been introduced to provide a higher-level API to pygltflib
- **b3dm**: support batchids with pygltflib
- **b3dm**: min/max attributes in gltf accessors
- **b3dm**: support materials & uvs with pygltflib
- **b3dm**: from_gltf also takes a feature table
- **pnts**: display info about batchtable when printing
- support intensity in pointcloud conversion, only in uint8 at the moment. Intensity of las files are converted from uint16 to uint8 at the moment.
- **tile.py**: add method to transform coords according to this tile transformation property
- **convert.py**: accept an existing out folders if empty
- **bounding_volume_box**: add classmethod .from_points and .from_list and document a bit
- We now have a logo!
- **tileset**: add mechanism to support extensions
- **base_tiler**: create an abstract tiler. This abstract class aims at making the creation of a custom tiler easier.

### Fix

- **tile.py**: write content URI as posix
- **typing**: quantized positions in pnts are uint16, not uint8
- **export**: fix optional import of psycopg2
- **tile.py**: make sure we reshape and flatten in column order
- **py3dtiles/tileset/content/b3dm.py**: sync the tile info after array initialization
- buildings.b3dm fixture is outdated
- **BatchTable**: ignore extensions in from_array
- **point_tiler**: set refine mode in the correct place
- **Tile**: don't raise error if file missing
- **docker**: move the workdir to /data in images
- **convert.py**:
    - don't crash on trying to remove non-existent path
    - fix transmission of worker error messages to main thread
- fix(b3dm.py): make node_matrix serializable

### Refactor

- **convert.py**: use our Tile and Tileset classes instead of dicts
- **tileset.py**: remove root_uri from constructor parameters
- **bounding_volume_box**: make sure transform accept only 4x4 matrices
- make export.py independant from home-made gltf
- print_info is replaced by __str__ properties for each tile_content
- **convert.py**:
    - remove unused parameter
    - simplify Process declaration
- move tiler point specific code outside of convert.py by using the abstract tiler
- move pytest fixtures into tests/conftest.py

### Miscellaneous

- for nix users, a shell.nix has been added to the project.

## v7.0.0 (2023-12-12)

### Community change: Big news!

**We welcome Lorenzo Marnat ([Liris](https://liris.cnrs.fr/)) as a new maintainer!** The Liris has contributed a lot to py3dtiles through their fork and the client application `py3dtilers` and Lorenzo is currently helping getting these improvements merged. This is a very important step forward developing our community and we're very glad to have him in the team.

As a result, we have made it so that py3dtiles is less tied to Oslandia and more to its own community. We hope to make contributions and implications even easier and open to other entities:

- **the repository has moved to its own organization**: https://gitlab.com/py3dtiles/py3dtiles and the main branch is now `main` instead of `master`. The existing issues and merge requests has been kept and the branch they point to has been updated. **Please update your git remotes**, especially because there is no redirection at the git level: we needed to recreate the py3dtiles on oslandia namespace to setup a redirection from the old pages.
- **The main domain is now `https://py3dtiles.org`**. A redirection has been made, but we still advise everybody to update their bookmarks
- We have a `GOVERNANCE.md` documentation that describes how the community will operate from now on.
- and we now have a [chat room](https://matrix.to/#/#py3dtiles:matrix.org) on matrix.org!

### BREAKING CHANGE

- `FeatureTable*` has been renamed to `PntsFeatureTable*`
- py3dtiles now requires numpy >= 1.24 to allow python 3.11 support (note: 3.12 support must wait for the next numba release)

Big change in the way we deal with dependencies. With more and more file format supports added, the dependency tree is becoming bigger and bigger. To avoid cluttering client environments with dependencies for formats they don't need, we are now using the `extras_require` section for some formats. Here is the list of file formats and the command to use to get the corresponding dependencies:

- postgresql support: `pip install py3dtiles[postgres]`
- las/laz support: `pip install py3dtiles[las]` (note: laz support is still conditioned by the presence of laszip or lasrs, see installation documentation)
- ply support: `pip install py3dtiles[ply]`

The `.[all]` sections allows to get all these dependencies. The docker image contains everything.

Csv and xyz support depends on the standard library, therefore they are always included.

### Feat

- add support for python 3.11
- add featureTable and B3dmFeatureTable classes
- upgrade numpy
- support for csv files and classification data in the xyz_reader

### Fix

- **mypy**: make type declarations compatible with python3.8
- **convert.py**: ensure the main process waits for all child to finish
- align b3dm_feature_table to 8 bytes
- Pnts from_file method to ensure TileContent is  PNTS
- PNTS ft body to_array returns one array
- **distance.py**: remove a numba warning
- **docker**: create it on bullseye to have liblaszip8

### Refactor

- **convert.py**: change self.idle_clients type to set
- reorder imports according to our isort config
- rename PNTS FeatureTable classes

## v6.0.0 (2023-04-04)

### BREAKING CHANGE

- `py3dtiles merge` now takes tileset path instead of a folder path.
- The class `BaseExtension` becomes an abstract class. Please use one of the subclasses
- `TileContentReader` class has been removed and its static methods are now plain functions in `tile_content_reader.py`.
- The `read_file` function has been renamed to `read_binary_tile_content` instance created with FeatureTableHeader.from_semantic method.
- the `queue` argument is removed from reader `run` method signatures (these functions do not send messages anymore)
- The method `sync` of the `PntsBody` and `B3dmBody` has been moved to `TileContent` class. The parameter `body` has been removed.
- The `Pnts.from_feature` method signature has completely changed. Numpy data type isn't used anymore but a `FeatureTableHeader`
- The attributes:
  - `B3dm.from_glTF` has been renamed to `B3dm.from_gltf`
  - `B3dmBody.from_glTF` has been renamed to `B3dmBody.from_gltf`
  - `B3dmBody.glTF` has been renamed to `B3dmBody.gltf`
- Few import changes:
  - Change `from py3dtiles.tileset.tile_content_reader import read_file` to `from py3dtiles.tileset.content import read_file`
  - Change `import py3dtiles.tileset.batch_table` to `import py3dtiles.tileset.content.batch_table`
  - Change `import py3dtiles.tileset.content.feature_table` in `import py3dtiles.tileset.content.feature_table`
  - The import of `TileContent` has been changed, now it is : `from py3dtiles.tileset.content import TileContent, TileContentBody, TileContentHeader`

- The type `ThreeDDictBase` has been renamed to `RootPropertyDictType`
- The class `Extendable` has been renamed to `RootProperty` and :
  - its method `add_extension` has been deleted, add directly to the attribute `extensions`
  - its method `has_extensions` has been deleted, check directly the content of the attribute `extensions`
  - its method `get_extension` has been deleted, retrieve directly the extension with its name in the dict attribute `extensions`
  - its method `get_extensions` has been deleted, get directly the attribute `extensions`
- The class `Tile` has been modified:
  - The `get_content` method has been renamed to `get_or_fetch_content`. If the `content` is already loaded or the `content_uri` is absolute, `root_uri` must be None.
  - The `set_content` method has been removed, set directly the attribute `tile_content`
  - The `set_content_uri` and Tile `get_content_uri` methods have been removed, set and get directly the `content_uri` attribute.
  - The method `get_children` has been renamed to `get_all_children`
  - The method `get_direct_children` has been deleted, use directly the attribute `children` to get them.
    Note: It is highly recommended to still use the method Tile.add_children (and not children.append)
  - The method `has_children` has been removed, check directly if the attribute `children` is empty.
- The class `TileSet` has been modified:
  - The `from_dict` requires a new parameter: `root_uri`, that is the folder where the tileset is.
  - The method `add_asset_extras()` has been deleted, use directly the attribute `extra` (dict)
  - The classes for tile content have been modified:
  - The class `TileContent` is now an abstract class, use `B3dm` or `Pnts` class instead
  - To create a `Pnts` or `B3dm` instance, you must indicate the header and the body instance in the constructor
  - The `TileContentType` class has been removed
  - The type attribute of the class `TileContentBody` has been removed
  - The class `Feature` has been removed
  - The `FeatureTableHeader.from_dtype` method has been replaced by `from_semantic`
  - The `positions_dtype`, `colors_dtype` and `normal_dtype` attributes of the class `FeatureTableHeader` has been removed. To get the data type, use
    `SEMANTIC_TYPE_MAP[semantic]` with semantic either `feature_table_header.positions`, `feature_table_header.colors` or `feature_table_header.normal`
  - The `FeatureTableBody.positions_arr` attribute has been renamed to `position`
  - The `FeatureTableBody.colors_arr` attribute has been renamed to `colors`
  - The `FeatureTableBody.positions_itemsize` has been removed
  - The `FeatureTableBody.colors_itemsize` has been removed
  - The `FeatureTableBody.from_features` method has been removed, use  `FeatureTable.from_features` instead
  - The `FeatureTableBody.positions` and `FeatureTableBody.colors` methods have  been removed,
    use `FeatureTable.get_feature_color_at` and `FeatureTable.get_feature_position_at` instead
  - The `FeatureTable.feature` method has been renamed to `get_feature_at` and return tuple instead of Feature instance
  - The signature of `FeatureTable.from_features` has completely changed. Numpy data type isn't anymore use,
    but a `FeatureTableHeader` instance created with `FeatureTableHeader.from_semantic()` method
-
### Feat

- Windows is fully supported
- a docker image is now built on each release
- Classification data can now be exported in the tileset
- Add an universal merger
- Load tileset from dictionary with lazy tile content loading
- Add methods to remove tilesets and tiles on disk
- Add the support of extras and extensions properties for Asset, BoundingVolume, Tile and TileSet
- Import and export extensionsUsed and extensionsRequired (TileSet)
- **tileset.py**: Sync root uri of tiles when the tileset is written as json
- **tileset.py**: Add methods `from_file` and `get_tile_contents`
- **tile.py**: The transformation attribute can be set in `__init__()`
- **bounding_volume.py**: Add new methods as abstractmethod
- new Py3dtiles exceptions have been created:
  - TilerException
  - ThreeDTileSpecError
  - PntsSpecError
  - B3dmSpecError
  - TilesetSpecError
  - BoundingVolumeMissingException
- Use transformation when sync bounding volume
- **feature_table.py**: Improve the support of pnts feature table
- **batch_table.py**: Allow mix of json and binary data
- Create a dedicated type for the export of the feature table header
- Add the Batch Table Hierarchy extension
- Add get_points method to PntsBody
- Add the from_points method in Pnts class
- Publish number_of_points_in_tileset on the API
- Typing work largely completed

### Fix

- **api.rst**: Correct the examples in the api doc
- Change gltf padding to fix b3dm body alignment
- **las_reader**: Correct color_scale calculation
- **convert.py**: Allow `convert` to work with the `spawn` multiprocess method
- Reverse the recursivity to prune from leafs to root instead of root to leafs
- allow multiple user to convert simultaneously on the same machine
- fix a warning about a 0 division that can occur when aabb have a 0-size dimension.

### Refactor

- Remove useless llvm dependency
- Retrieve crs with laspy instead of pdal and remove the pdal dependency
- Rename `read_file` function to `read_binary_tile_content`
- Move `print_b3dm_info` and `print_pnts_info` in the `tile_content` classes
-
- use tile.content_uri in write_to_directory method
- **merger.py**: use tileset module instead of using custom tools
- **bounding_volume_box.py**: improve the readability of some methods
- use fix size numpy data type (`np.uint8` instead of `np.ubytes`)
- explicit re-export module with a better API import style
-
- move all node_process functions in a class to clean/simplify code
- move the main node processing loop to `convert.py` for centralizing message sending
- yield node process and send message in the main node processing function
- Remove useless try..except blocks
- `halt_at_depth` defined starting from node name length
- Remove `node_catalog` parameter of `insert` and _`split` methods since it is useless.
- yield node process and send message with yielded values [WIP]
- Reader `run` methods now yields tuples of coordinate, color and classification arrays and the message is sent by the Worker object
- **pnts_writer.py**: `run` method now yields the total amount of nodes and the message is sent by the Worker object
- transform `TileContent` class to abstract class and add typing info
- **tileset/utils.py**: The static methods in `TileContentReader` become functions in a dedicated `tile_content_reader.py` module
- Lowercase all `glTF` occurrences
- **node.py**: Rename `reminder` occurrences to `remainder`

## v5.0.0 (2023-02-02)

### BREAKING CHANGE

- py3dtiles no longer support python 3.7 (it reaches EOL in june)
- The function convert_to_ecef has been removed
- Many imports have been changed, please update them accordingly:
    - `from py3dtiles import B3dm` becomes `from py3dtiles.tileset.content import B3dm`
    - `from py3dtiles import GlTF` becomes `from py3dtiles.tileset.content import GlTF`
    - `from py3dtiles import Pnts` becomes `from py3dtiles.tileset.content import Pnts`
    - `from py3dtiles import BatchTable` becomes `from py3dtiles.tileset.batch_table import BatchTable`
    - `from py3dtiles import BoundingVolumeBox` becomes `from py3dtiles.tileset.bounding_volume_box import BoundingVolumeBox`
    - `from py3dtiles import Extendable` becomes `from py3dtiles.tileset.extendable import Extendable`
    - `from py3dtiles import Extension` becomes `from py3dtiles.tileset.extension import BaseExtension`
    - `from py3dtiles import Tile` becomes `from py3dtiles.tileset.tile import Tile`
    - `from py3dtiles import TileContent` becomes `from py3dtiles.tileset.tile_content import TileContent`
    - `from py3dtiles import TileSet` becomes `from py3dtiles.tileset.tileset import TileSet`
    - `from py3dtiles import TileContentReader` becomes `from py3dtiles.tileset.utils import TileContentReader`
    - `from py3dtiles import TriangleSoup` becomes `from py3dtiles.tilers.b3dm.wkb_utils import TriangleSoup`
    - `from py3dtiles import Feature` becomes `from py3dtiles.tileset.feature_table import Feature`
- The BoundingVolume class become an abstract class
- The way of getting / setting `transform` has changed:
    - The methods `set_transform` and `get_transform` of the class `Tile` has been removed, and the attribute `transform` of the class `Tile` has been renamed from `_transform` to `transform.` Please use the attribute directly.
    - in the same vein, the method `set_transform` of the class `Tileset` has been removed
    - The method set_from_array from the class BoundingVolumeBox has been removed, use set_from_list instead (with an ArrayLike)
- some parameters types have been set to always be a flat numpy array of `np.float64`:
    - `Tile.transform`
    - The parameter `offset` of the method `BoundingVolumeBox.translate`
    - The parameter `transform` of the method `BoundingVolumeBox.transform`
    - The parameter `box_list` of the method `BoundingVolumeBox.set_from_list`
    - The parameter `mins_maxs` of the method `BoundingVolumeBox.get_box_array_from_mins_maxs`
    - The parameter `points` of the method `BoundingVolumeBox.get_box_array_from_point`

### Features

- **convert.py**: add parameter to ignore CRS mixin in input files
- add the import and export of batch table from pnts (only json)
- **reader/ply_reader.py**: support .ply files
- **typing.py**: create the tileset json structure with typing annotations


### Fixes

- add and update typing annotations to fix all mypy issues
- check magic value as bytes not str
- exclude B028 flake8 rule
- **node.py**: delete tile children when the tile root is moved in a sub tileset

### Refactor

- remove all asserts in source code
- select only used fonctions from transformation file and update the code
- **LICENSE**: remove Mapbox third party license
- remove copied earcut code and use mapbox library
- change file hierarchy


## v4.0.0 (2023-01-09)

### BREAKING CHANGE

- The parameter `srs_in` and `srs_out` of `py3dtiles.convert.convert` have been
renamed to `crs_in` and `crs_out`. Furthermore, their type is no longer int
or str but `pyproj.CRS`. No change has been made to the command-line `py3dtiles convert`, but you can use proj4 string in addition to epsg code. To migrate old code, instead of:
```python
from py3dtiles.convert import convert
# ...
convert('without_srs.las', outfolder=tmp_dir, crs_out='4978')
```
you can do:
```python
from pyproj import CRS
from py3dtiles.convert import convert
# ...
convert('without_srs.las', outfolder=tmp_dir, crs_out=CRS.from_epsg(4978))
```
- SrsInMissingException has been moved from `py3dtiles/utils.py` to `py3dtiles/exceptions.py`.

### Feat

The main feature of this release is that you can now mix las/laz/xyz files in one invocation of the convert function.

### Fix

- **shared_node_store.py**: fix node removing in cache if already deleted
- change srs_in to srs_out to fix refactoring error
- avoid duplicate points when the mode is replace

### Refactor

- **convert**: rename the 'infos' variable and function to 'file_info'
- **convert**: use CRS almost everywhere instead of string representing epsg code
- **exceptions**: move all custom exceptions at the same place
- **convert**: use a dictionary to find the correct reader
- fix issues find by pre-commit

### Chores

- add pre-commit hooks

## v3.0.0

### BREAKING

Some renaming has been done to better follow the 3dtiles specification:

- `TileHeader` -> `TileContentHeader`
- `TileBody` -> `TileContentBody`
- The API of merger.py::merge wasn't really convenient to use and has now changed. Now the signature is:
```python3
def merge(folder: Union[str, Path], overwrite: bool = False, verbose: int = 0) -> None
```
- the argument verbose of the cli interface has changed. To increase the verbosity, the number of -v is counted (-vv will be a verbose of 2).
- Boolean options has been changed from `--foo=1` to simple flags: `--foo`. Affected options are `--overwrite` and `--graph`.
- `--rgb=no` has been replaced by a `--no-rgb` option to deactivate it. The default is still to keep color information

### Features

- support laz if laszip is installed
- windows support (NOTE: testers needed)
- Some classes to represent 3Dtiles concepts have been added:
	- BoundingVolumeBox
	- TileSet
	- Tile
	- uExtension

### Fix

- The geometric error of two merged tilesets is now the biggest of the two tileset geometric error divided by the ratio of kept points. We believe this use of GeometricError fits more the spirit of the specification.
- **node**: avoid empty children array in tileset.json
- **setup.py**: fix missing dependency pytest
- **node**: avoid to add empty children array
- disable padding if already 8-byte aligned instead of adding 8 new empty bytes
- **featureTable**: add a 8-byte boundary for FeatureTableBody
- **featureTable**: change the boundary from 4 to 8
- replace sys.exit(1) in convert by raising an exception

## v2.0.0

This releases completely reworks py3dtiles command line and add new features.

The command line now uses subcommands syntax, in order to expose a single
entry point and support multiple commands. The existing commands 'export_tileset' and 'py3dtiles_info' became
'py3dtiles export' and 'py3dtiles info'.

### Changes

- relicensed as Apache 2.0.
- minimal python supported is now 3.8
- dependencies versions has been updated:
    - laspy should be at least 2.0
    - numpy at least 1.20.0
- Tile has been renamed to TileContent

### Features

New features were added, the main one being: py3dtiles can be used to convert
pointcloud las files to a 3dtiles tileset.

This is the purpose of the 'py3dtiles convert' command. It supports multicore
processor for faster processing, leveraging pyzmq, and the memory management has been carefully
implemented to support virtually unlimited points count.

Other features:

- read points from xyz files
- Documentation are now published at https://oslandia.gitlab.io/py3dtiles

### Fixes

* 53580ba Jeremy Gaillard       fix: use y-up orientation for glTF objects in export script
* 65d6f67 Jeremy Gaillard       fix: proper bounding box size in export script
* 3603b00 Augustin Trancart     fix: reliably select triangulation projection plane and orientation
* fd2105a jailln                Fix gltf min and max value
