# Docker

This documentation is intented for developers and contributors. For installation option, please see [the installation documentation](../docs/install.rst).

## How to build the docker image

You must run the following command in the root folder of the repository:
```bash
docker build . -t py3dtiles/py3dtiles:v8.0.0 -t registry.gitlab.com/py3dtiles/py3dtiles:v8.0.0 -f docker/Dockerfile
```
Then `docker push` the 2 tags. It will push on dockerhub.com and on registry.gitlab.com.

NOTE: the CI does that automatically on each tag.

## How to use the docker image

The docker image has a volume on `/data/` and the entrypoint is directly the command `py3dtiles`.

#### Examples

Display the help
```bash
docker run -it --rm py3dtiles --help
```

Convert a file into 3d tiles
```bash
docker run -it --rm \
    --mount type=bind,source="$(pwd)",target=/data/ \
    --volume /etc/passwd:/etc/passwd:ro --volume /etc/group:/etc/group:ro --user $(id -u):$(id -g) \
    py3dtiles \
    convert <file>
```

NOTE:

- the `--mount` option is necessary for docker to read your source data and to write the result. The way it is written in this example only allows you to read source files in the current folder or in a subfolder
- This line `--volume /etc/passwd:/etc/passwd:ro --volume /etc/group:/etc/group:ro --user $(id -u):$(id -g)` is only necessary if your uid is different from 1000.
