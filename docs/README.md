# Doc of py3dtiles

## How to generate the doc?

First install dependencies in a python3 virtualenv:

```
pip install -e .
pip install -e .[doc]
```

API doc structure is generated with
```
SPHINX_APIDOC_OPTIONS="members,show-inheritance" sphinx-apidoc -o ./api ../py3dtiles
```
This command needs to be used only when new files are added (TODO check if sphinx-autoapi wouldn't do this job for us?)

To regenerate the doc for one version:

```
sphinx-build -A current_version=HEAD -A "versions=[main]" -b html docs ./_build/html
```
(NOTE: For some reason, `make clean` in the `docs/` folder is often necessary if the toctree changes)

To generate the doc as gitlab does it:

```
sphinx-multiversion . <outfolder>
```
