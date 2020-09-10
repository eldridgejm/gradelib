with import <nixpkgs> {};

mkShell {

  buildInputs = with python38Packages; [
    venvShellHook
  ];

  venvDir = ".venv";

  postShellHook = ''
    pip install black pytest ipython
    pip install -r requirements.txt
  '';

}
