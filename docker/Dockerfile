FROM python:3.12-slim-bullseye

# system dependencies
RUN apt-get update && apt-get install -y liblaszip8 \
    && rm -rf /var/lib/apt/lists/*

# create an unprivileged user
RUN useradd py3dtiles

# prepare work env
RUN mkdir /data
RUN chown py3dtiles:py3dtiles /data
VOLUME /data

# prepare app dir
WORKDIR /app

# allow numba to do its thing even with unprivileged user
ENV NUMBA_CACHE_DIR=/tmp

# install dependencies
# NOTE we don't install py3dtiles just yet, only dependencies,
# This way, the layer created by the next instruction won't change very often and it'll save space
COPY docker/requirements.txt requirements.txt
RUN pip3 install -r requirements.txt && pip cache purge

# Copy necessary files
COPY pyproject.toml pyproject.toml
COPY py3dtiles py3dtiles
COPY README.rst README.rst
# install py3dtiles
RUN pip install .

# Then switch to unprivileged user
WORKDIR /data
USER py3dtiles

# configure the entrypoint
ENTRYPOINT ["py3dtiles"]
