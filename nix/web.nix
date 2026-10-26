{
  lib,
  buildNpmPackage,
  nodejs_24,
}:

buildNpmPackage {
  pname = "journal-search-web";
  version = "0.1.0";
  src = ../web;

  nodejs = nodejs_24;
  npmDepsHash = "sha256-Yhl34DPR5bHoVJSQxiyRZQipy4MkkvrXQkroGvqkEVw=";

  dontNpmInstall = true;
  installPhase = ''
    runHook preInstall
    mkdir -p "$out"
    cp -r dist/. "$out"
    runHook postInstall
  '';

  meta = {
    description = "Journal Search web UI";
    platforms = lib.platforms.linux;
  };
}
