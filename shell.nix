{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = with pkgs; [
    python314
    uv
    tesseract
    poppler-utils
    llama-cpp  # For Surya OCR
    # For pillow and other native libs
    zlib
    libjpeg
    libpng
    pkg-config
    # C++ standard library for numpy/torch
    stdenv.cc.cc.lib
  ];

  # Set library path for dynamically linked libs
  LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath [
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
}
