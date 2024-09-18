# Doc of py3dtiles

The documentation is generated with sphinx.

## How to generate the doc?

First install dependencies in a python3 virtualenv:

```
pip install -e .
pip install -e .[doc]
```
The principle is the following:

- `sphinx-multiversion` checkouts each tags and executes `sphinx-build` on it.
- `spinxcontrib-apidoc` plugs `sphinx-apidoc` to each execution of `sphinx-build`, so that the api doc of the website is auto-generated.

To regenerate the doc for one version, from this folder:

```
sphinx-build -A current_version=HEAD -A "versions=[main]" -b html . ../_build/html
```
(NOTE: For some reason, `make clean` in the `docs/` folder is often necessary if the toctree changes)

To generate the doc as gitlab does it:

```
sphinx-multiversion . <outfolder>
```
