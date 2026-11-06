#!/bin/sh
# Bild für die Vignette übernehmen: tools/vignette_import.sh <datei> <name>, z. B. morgen-sonne-oel
# Schneidet höchstens auf 21:9 zu (Mitte) und speichert eine große und eine kleine WebP-Version.
set -e
in="$1"; name="$2"; dir="$(dirname "$0")/../static/vignette"
mkdir -p "$dir"
crop="crop='min(iw,ih*21/9)':'min(ih,iw*9/21)'"
ffmpeg -loglevel error -y -i "$in" -vf "$crop,scale=2000:-2" -quality 82 "$dir/$name.webp"
ffmpeg -loglevel error -y -i "$in" -vf "$crop,scale=960:-2" -quality 80 "$dir/$name-klein.webp"
echo "$dir/$name.webp"
