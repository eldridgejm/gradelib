with import <nixpkgs> {};
with python37Packages;

buildPythonPackage rec {
  name = "gradelib";
  src = ./.;
  propagatedBuildInputs = [ pandas numpy ];
  nativeBuildInputs = [ black pytest jupyter ipython ];
}
