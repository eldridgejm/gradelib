{
  description = "Python package for streamlining end-of-quarter grading.";

  inputs.nixpkgs.url = github:NixOS/nixpkgs/21.11;

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
                poetry-core
              ];

            }
          );

        defaultPackage = forAllSystems (system:
            self.gradelib.${system}
          );

        devShell = forAllSystems (system:
          let
            pkgs = import nixpkgs {
              inherit system;
            };

          in
            pkgs.mkShell {
              buildInputs = [
                pkgs.gnumake
                pkgs.poetry
              ];

              shellHook = ''
              poetry install
              export PATH=$(poetry env info -p)/bin:$PATH
              export PYTHONPATH=$(poetry env info -p)/lib/python3.8/site-packages:$PYTHONPATH
              export LD_LIBRARY_PATH=${pkgs.lib.makeLibraryPath [pkgs.stdenv.cc.cc]}
              '';
            }
        );

      };

}
