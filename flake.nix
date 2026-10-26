{
  description = "Self-hosted journal OCR and search";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

    pyproject-nix = {
      url = "github:pyproject-nix/pyproject.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    uv2nix = {
      url = "github:pyproject-nix/uv2nix";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    pyproject-build-systems = {
      url = "github:pyproject-nix/build-system-pkgs";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.uv2nix.follows = "uv2nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    {
      self,
      nixpkgs,
      uv2nix,
      pyproject-nix,
      pyproject-build-systems,
    }:
    let
      inherit (nixpkgs) lib;
      systems = [
        "x86_64-linux"
        "aarch64-linux"
      ];
      forAllSystems = lib.genAttrs systems;

      workspace = uv2nix.lib.workspace.loadWorkspace { workspaceRoot = ./.; };
      overlay = workspace.mkPyprojectOverlay { sourcePreference = "wheel"; };

      pythonSets = forAllSystems (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          python = pkgs.python312;
        in
        (pkgs.callPackage pyproject-nix.build.packages { inherit python; }).overrideScope (
          lib.composeManyExtensions [
            pyproject-build-systems.overlays.wheel
            overlay
          ]
        )
      );
    in
    {
      packages = forAllSystems (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          pythonSet = pythonSets.${system};
          venv = pythonSet.mkVirtualEnv "echo-env" workspace.deps.default;
          web = pkgs.callPackage ./nix/web.nix { };
        in
        {
          web = web;
          default = pkgs.stdenv.mkDerivation {
            pname = "echo";
            version = "0.1.0";
            dontUnpack = true;
            nativeBuildInputs = [ pkgs.makeWrapper ];
            installPhase = ''
              runHook preInstall
              mkdir -p "$out/bin"
              makeWrapper ${venv}/bin/python "$out/bin/echo" \
                --prefix PATH : ${lib.makeBinPath [ pkgs.tesseract ]} \
                --set-default WEB_ROOT ${web} \
                --add-flags "-m" \
                --add-flags "echo"
              runHook postInstall
            '';
            passthru = {
              inherit venv web;
            };
            meta = {
              description = "Self-hosted journal OCR and semantic search";
              mainProgram = "echo";
              platforms = lib.platforms.linux;
            };
          };
        }
      );

      devShells = forAllSystems (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
        in
        {
          default = pkgs.mkShell {
            packages = with pkgs; [
              python314
              uv
              tesseract
              poppler-utils
              llama-cpp
              zlib
              libjpeg
              libpng
              pkg-config
              stdenv.cc.cc.lib
            ];
            env.LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath [
              pkgs.stdenv.cc.cc.lib
              pkgs.zlib
              pkgs.libjpeg
              pkgs.libpng
            ];
            shellHook = ''
              if [ ! -d .venv ]; then
                uv venv
              fi
              source .venv/bin/activate
            '';
          };
        }
      );

      nixosModules.default = import ./nix/module.nix { inherit self; };

      checks = lib.optionalAttrs (builtins.elem "x86_64-linux" systems) {
        x86_64-linux.module =
          let
            pkgs = nixpkgs.legacyPackages.x86_64-linux;
          in
          pkgs.testers.nixosTest {
            name = "echo";
            nodes.machine =
              { pkgs, ... }:
              {
                imports = [ self.nixosModules.default ];
                environment.systemPackages = [ pkgs.curl ];
                services.echo = {
                  enable = true;
                  ollama.enable = false;
                };
              };
            testScript = ''
              machine.wait_for_unit("echo.service")
              machine.wait_for_open_port(8000)
              machine.succeed("curl -fsS http://127.0.0.1:8000/health")
              machine.succeed("curl -fsS http://127.0.0.1:8000/api/v1/auth/config | grep needs_setup")
              machine.succeed("curl -fsS http://127.0.0.1:8000/ | grep -i '<title>'")
            '';
          };
      };
    };
}
