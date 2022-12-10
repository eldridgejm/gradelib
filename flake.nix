{
  description = "Python package for streamlining end-of-quarter grading.";

  inputs.nixpkgs.url = github:NixOS/nixpkgs/nixpkgs-unstable;

  outputs = { self, nixpkgs }:
    let
      supportedSystems = [ "x86_64-linux" "x86_64-darwin" "aarch64-darwin" ];
      forAllSystems = f: nixpkgs.lib.genAttrs supportedSystems (system: f system);

      overlays = [(
          self: super: {

            # update version of sphinx to get feature that adds all functions, methods,
            # etc. to navigation
            python310 = super.python310.override {
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

                        propagatedBuildInputs = attrs.propagatedBuildInputs ++ [
                            python-super.flit-core
                          ];
                    });
                  };
                };
          }
      )];
    in
      {
        gradelib = forAllSystems (system:
          with import nixpkgs { system = "${system}"; allowBroken = true; overlays = overlays; };
            python310Packages.buildPythonPackage rec {
              name = "gradelib";
              src = ./.;
              propagatedBuildInputs = with python310Packages; [ pandas altair matplotlib numpy ];
              nativeBuildInputs = with python310Packages; [ pytest ipython sphinx sphinx_rtd_theme ];
            }
          );

        defaultPackage = forAllSystems (system:
            self.gradelib.${system}
          );
      };

}
