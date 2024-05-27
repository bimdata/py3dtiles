# Nix(OS) packaging

This folder contains nix files for [nix and nixos](https://nixos.org/) packaging.

## Dev shell

```
nix-shell pip-shell.nix
```
This will first start a shell with python 3.11 then create a virtualenv in `.venv` if it doesn't exist yet.

## Packaging

Not yet done! We need:

- a derivation
- either a default.nix for nixpkgs version or a flake.nix
