#!/bin/sh
# Render the PNG variants of the HexCalibr brand kit from its SVGs (headless Chrome, macOS path).
# Run from anywhere: brand/render_png.sh
set -e
cd "$(dirname "$0")"
CHROME=${CHROME:-"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"}
shot() {  # html size_w size_h out
  printf '%s' "$1" > _r.html
  "$CHROME" --headless=new --disable-gpu --hide-scrollbars --default-background-color=00000000 \
    --window-size="$2,$3" --screenshot="$PWD/$4" "file://$PWD/_r.html" >/dev/null 2>&1
}
# icon: transparent, 92 % of the square
for s in 512 256 64; do
  for v in icon icon-dark; do
    shot "<html><body style=\"margin:0;width:${s}px;height:${s}px;display:flex;justify-content:center;align-items:center\"><img src=\"icon/$v.svg\" style=\"max-width:92%;max-height:92%\"></body></html>" $s $s "icon/$v-$s.png"
  done
done
# word mark: transparent, 1200 px wide
for v in wordmark wordmark-dark; do
  shot "<html><body style=\"margin:0;width:1200px;height:320px;display:flex;align-items:center\"><img src=\"wordmark/$v.svg\" style=\"width:1200px\"></body></html>" 1200 320 "wordmark/$v-1200.png"
done
# social card 1200x630 and GitHub avatar 512 (opaque backgrounds)
shot '<html><body style="margin:0;width:1200px;height:630px;background:#16191d;display:flex;justify-content:center;align-items:center"><img src="wordmark/wordmark-dark.svg" style="width:960px"></body></html>' 1200 630 social/og-image.png
shot '<html><body style="margin:0;width:512px;height:512px;background:#f7f6f3;display:flex;justify-content:center;align-items:center"><img src="icon/icon.svg" style="height:430px"></body></html>' 512 512 social/avatar-github.png
rm -f _r.html
echo "PNGs rendered"
