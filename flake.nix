{
  description = "Python package for streamlining end-of-quarter grading.";

  inputs.nixpkgs.url = github:NixOS/nixpkgs/nixos-23.11;

  outputs = {
    self,
    nixpkgs,
  }: let
    supportedSystems = ["x86_64-linux" "x86_64-darwin" "aarch64-darwin"];
    forAllSystems = f: nixpkgs.lib.genAttrs supportedSystems (system: f system);

    overlays = [
      (
        self: super: {
          # update version of sphinx to get feature that adds all functions, methods,
          # etc. to navigation
          python3 = super.python3.override {
            packageOverrides = python-self: python-super: {
              sphinx = python-super.sphinx.overridePythonAttrs (attrs: {
                version = "5.2.3";
                format = "pyproject";

                src = self.fetchFromGitHub {
                  owner = "sphinx-doc";
                  repo = "sphinx";
                  rev = "refs/tags/v5.2.3";
                  hash = "sha256-DvMPrg2KchbWmo2E1qFZN45scSqwwe47y1gBIiSkjbM=";
                };

                propagatedBuildInputs =
                  attrs.propagatedBuildInputs
                  ++ [
                    python-super.flit-core
                  ];
              });
            };
          };
        }
      )
    ];
  in rec {
    gradelib = forAllSystems (
      system:
        with import nixpkgs {
          system = "${system}";
          allowBroken = true;
          overlays = overlays;
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
          overlays = overlays;
        };
          mkShell {
            buildInputs = with python3Packages; [
              pytest
              sphinx
              sphinx_rtd_theme
              jupyterlab

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
