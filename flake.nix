{
  description = "Development shell with custom Python environment and sumtree package";

  inputs = {
#     nixpkgs.url = "github:nixos/nixpkgs?ref=nixos-unstable";
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.11";
  };

  outputs =
    { self, nixpkgs }:
    let
      system = "x86_64-linux";
      pkgs = import nixpkgs { inherit system; };
      myPython = pkgs.python313.override {
        packageOverrides = final: prev: {

        };
      };

      myPythonEnv = myPython.withPackages (ps: [
#         ps.openai
#         ps.pydantic
        ps.requests
      ]);

      sumtree = pkgs.writeShellScriptBin "sumtree" ''
        exec ${myPythonEnv}/bin/python ${self}/sumtree.py "$@"
      '';
    in
    {
      packages.${system} = {
        sumtree = sumtree;
        default = sumtree;
      };

      devShells.${system}.default = pkgs.mkShell {
        packages = [
          myPythonEnv
          sumtree
        ];

        shellHook = ''
          if [[ $- == *i* ]]; then
            export PS1="[sumtree-dev:\w] "
          fi
        '';
      };
    };
}