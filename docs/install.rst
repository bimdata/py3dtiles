Install
-------

From pypi
~~~~~~~~~~~~

`py3dtiles` is published on pypi.org.

.. code-block:: shell

    pip install py3dtiles

Please read the section ":ref:`File formats support`" next.

From sources
~~~~~~~~~~~~

To use py3dtiles from sources:

.. code-block:: shell

    $ apt install git python3 python3-pip virtualenv
    $ git clone git@gitlab.com:py3dtiles/py3dtiles.git
    $ cd py3dtiles
    $ virtualenv -p python3 venv
    $ . venv/bin/activate
    (venv)$ pip install .

You might need to install specific format dependencies as described in the section "From pypi".

If you want to run unit tests:

.. code-block:: shell

    (venv)$ pip install -e .[dev]
    (venv)$ pytest

Please read the section ":ref:`File formats support`" next.

.. _File formats support:

File formats support
~~~~~~~~~~~~~~~~~~~~

By default, no specific format dependencies are installed. You should either install them separately, or use our `extra_requires` sections:

.. code-block:: shell

    # las support
    pip install py3dtiles[las]
    # ply
    pip install py3dtiles[ply]
    # postgres
    pip install py3dtiles[postgres]
    # everything at once
    pip install py3dtiles[postgres,ply,las]


To support laz files you need an external library and a laz backend for
laspy, see [this link]](https://laspy.readthedocs.io/en/latest/installation.html#pip). Short answer, for laszip, you need to follow these steps:

.. code-block:: shell

  $ # install liblaszip, for instance on ubuntu 22.04
  $ apt-get install -y liblaszip8

  $ # Install with LAZ support via laszip
  $ pip install laspy[laszip]


If you don't need waveform support, lazrs is also a good option.

From docker
~~~~~~~~~~~~

We currently publish docker images on gitlab registry. Please see [the currently published versions](https://gitlab.com/py3dtiles/py3dtiles/container_registry/4248842).
```
docker run --rm registry.gitlab.com/py3dtiles/py3dtiles:<version> --help
```


NOTE:

- the `--mount` option is necessary for docker to read your source data and to write the result. The way it is written in this example only allows you to read source files in the current folder or in a subfolder
- This line `--volume /etc/passwd:/etc/passwd:ro --volume /etc/group:/etc/group:ro --user $(id -u):$(id -g)` is only necessary if your uid is different from 1000.
