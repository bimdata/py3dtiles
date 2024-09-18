"""
This is the root module of the py3dtiles project.

If you develop an application using py3dtiles, you are most probably interested in:

- the :py:func:`.py3dtiles.convert.convert` function, allowing you to launch conversion jobs directly from your python code
- the :py:mod:`.py3dtiles.tileset` package, as it contains supporting classes for reading and writing tilesets.

If you are looking for a way to extend py3dtiles conversion capabilities, or to write your own tiler, you should have a look at the :py:mod:`.py3dtiles.reader` package or the :py:mod:`.py3dtiles.tilers` package.

All client applications should use the :py:mod:`py3dtiles.exceptions` module, which contains all the exceptions that py3dtiles might throw.

"""
__version__ = "8.0.2"
