#!/usr/bin/env bash
# Régénère les mipmaps Android depuis les SVG de ../assets.
# Dépend de rsvg-convert (librsvg). Les PNG produits sont versionnés :
# à ne relancer que si les sources changent.
set -euo pipefail

cd "$(dirname "$0")/.."
SRC=assets
RES=android/app/src/main/res

# densité:taille legacy (48dp):taille adaptative (108dp)
for entry in mdpi:48:108 hdpi:72:162 xhdpi:96:216 xxhdpi:144:324 xxxhdpi:192:432; do
  IFS=: read -r dpi legacy adaptive <<<"$entry"
  out="$RES/mipmap-$dpi"
  mkdir -p "$out"
  rsvg-convert -w "$legacy"   -h "$legacy"   "$SRC/icon.svg"            -o "$out/ic_launcher.png"
  rsvg-convert -w "$legacy"   -h "$legacy"   "$SRC/icon-round.svg"      -o "$out/ic_launcher_round.png"
  rsvg-convert -w "$adaptive" -h "$adaptive" "$SRC/icon-foreground.svg" -o "$out/ic_launcher_foreground.png"
  echo "$dpi : ${legacy}px legacy + ${adaptive}px adaptatif"
done
