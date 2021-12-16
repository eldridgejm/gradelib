{
  description = "Python package for streamlining end-of-quarter grading.";

  inputs.nixpkgs.url = github:NixOS/nixpkgs/20.03;

  outputs = { self, nixpkgs }: 
    let
      supportedSystems = [ "x86_64-linux" "x86_64-darwin" ];
      forAllSystems = f: nixpkgs.lib.genAttrs supportedSystems (system: f system);
    in
      {
        gradelib = forAllSystems (system:
          with import nixpkgs { system = "${system}"; };
            python3Packages.buildPythonPackage rec {
              name = "gradelib";
              src = ./.;
              format = "pyproject";

              propagatedBuildInputs = with python3Packages; [ 
                pandas
                matplotlib
                numpy
              ];
              nativeBuildInputs = with python3Packages; [
                black
                pytest
                ipython
                sphinx
                sphinx_rtd_theme
                mypy
              ];
            }
          );

        defaultPackage = forAllSystems (system:
            self.gradelib.${system}
          );

        devShell = forAllSystems (system:
          let
            pkgs = import nixpkgs { system = "${system}"; };
          in
            pkgs.mkShell {
              buildInputs = [
                (
                  pkgs.python3.withPackages (p: [
                    # self.gradelib.${system}
                    p.poetry
                  ])
                )
              ];
            }
        );
      };

}
