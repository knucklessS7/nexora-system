#!/usr/bin/env bash
set -euo pipefail

source_image=${1:?Uso: compress-image.sh IMAGEM.img [SAIDA.img.gz]}
final_archive=${2:-"${source_image}.gz"}
partial_archive="${final_archive}.partial.$$"

cleanup() { rm -f -- "$partial_archive"; }
trap cleanup EXIT INT TERM

test -f "$source_image"
gzip -6 -c -- "$source_image" > "$partial_archive"
gzip -t -- "$partial_archive"
mv -f -- "$partial_archive" "$final_archive"
trap - EXIT INT TERM
sha256sum "$final_archive"
