{ pkgs ? import <nixpkgs> { } }:
pkgs.mkShell rec {
  name = "impurePythonEnv";
  buildInputs = [
    pkgs.python311
  ];

  shellHook = ''
    set -h #remove "bash: hash: hashing disabled" warning !
    # https://nixos.org/manual/nixpkgs/stable/#python-setup.py-bdist_wheel-cannot-create-.whl
    SOURCE_DATE_EPOCH=$(date +%s)
    # Let's allow compiling stuff
    export LD_LIBRARY_PATH="${pkgs.lib.makeLibraryPath (with pkgs; [ zlib stdenv.cc.cc ])}":LD_LIBRARY_PATH;

    if ! [ -d .venv ]; then
      python -m venv .venv
    fi

    source .venv/bin/activate

    export TMPDIR=/tmp/pipcache

    if [ ! -x .venv/bin/py3dtiles ] > /dev/null 2>&1; then
      python -m pip install --cache-dir=$TMPDIR --upgrade pip
      python -m pip install --cache-dir="$TMPDIR" -e .\[postgres,las,ply,dev,doc,pack\]
      # keep this line after so that ipython deps doesn't conflict with other deps
      python -m pip install ipython debugpy
    fi
  '';
}
