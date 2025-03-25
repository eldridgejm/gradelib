{
  description = "Python package for streamlining end-of-quarter grading.";

  inputs.nixpkgs.url = github:NixOS/nixpkgs/nixos-24.11;

  outputs = {
    self,
    nixpkgs,
  }: let
    supportedSystems = ["x86_64-linux" "x86_64-darwin" "aarch64-darwin"];
    forAllSystems = f: nixpkgs.lib.genAttrs supportedSystems (system: f system);
  in rec {
    gradelib = forAllSystems (
      system:
        with import nixpkgs {
          system = "${system}";
          allowBroken = true;
        };
          python3Packages.buildPythonPackage rec {
            name = "gradelib";
            format = "pyproject";
            src = ./.;
            propagatedBuildInputs = with python3Packages; [pandas bokeh matplotlib numpy];
            nativeBuildInputs = with python3Packages; [setuptools wheel pip];
            doCheck = false;
          }
    );

    devShell = forAllSystems (
      system:
        with import nixpkgs {
          system = "${system}";
          allowBroken = true;
        };
          mkShell {
            buildInputs = with python3Packages; [
              pytest
              sphinx
              sphinxawesome-theme
              jupyterlab
              ruff

              # install gradelib package to 1) make sure it's installable, and
              # 2) to get its dependencies. But below we'll add it to PYTHONPATH
              # so we can develop it in place.
              gradelib.${system}
            ];

            shellHook = ''
              export PYTHONPATH="$(pwd)/src/:$PYTHONPATH"
            '';
          }
    );

    defaultPackage = forAllSystems (
      system:
        self.gradelib.${system}
    );
  };
}
