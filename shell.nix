with import <nixpkgs> {};
with python37Packages;

buildPythonPackage rec {
  name = "gradelib";
  src = ./.;
  propagatedBuildInputs = [ pandas matplotlib numpy ];
  nativeBuildInputs = [ black pytest jupyter ipython sphinx sphinx_rtd_theme ];
}
