{
  description = "Python package for streamlining end-of-quarter grading.";

  inputs.nixpkgs.url = github:NixOS/nixpkgs/nixpkgs-unstable;

  outputs = { self, nixpkgs }: 
    let
      supportedSystems = [ "x86_64-linux" "x86_64-darwin" "aarch64-darwin" ];
      forAllSystems = f: nixpkgs.lib.genAttrs supportedSystems (system: f system);
    in
      {
        gradelib = forAllSystems (system:
          with import nixpkgs { system = "${system}"; allowBroken = true; };
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
