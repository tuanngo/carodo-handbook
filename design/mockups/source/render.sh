#!/bin/sh
# Renders the first-run mockup boards to PNG with headless Chrome (like brand/source/build.sh).
set -e
here="$(cd "$(dirname "$0")" && pwd)"
chrome="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
shot() { # file width height out
  mkdir -p "$(dirname "$here/../$4")"
  "$chrome" --headless=new --disable-gpu --hide-scrollbars --allow-file-access-from-files \
    --force-device-scale-factor=1 --window-size="$2,$3" --screenshot="$here/../$4" "file://$here/$1" 2>/dev/null
}
shot first-run-day0.html 1720 4560 onboarding/first-run-day0.png
[ -f "$here/first-run-day1.html" ] && shot first-run-day1.html 1880 3230 onboarding/first-run-day1.png
shot auto-mode.html 1720 2150 drive/auto-mode.png
shot recording-polish.html 1800 5380 drive/recording-polish.png
shot journey-trim.html 1880 5060 journeys/journey-trim.png
# Frames are 3x: rendered at 2x so the map stays sharp.
"$chrome" --headless=new --disable-gpu --hide-scrollbars --allow-file-access-from-files \
  --force-device-scale-factor=2 --window-size=1720,2720 --screenshot="$here/../replay/replay-video-frame.png" "file://$here/replay-video.html" 2>/dev/null
shot replay-export.html 1900 2150 replay/replay-export.png
shot share-card.html 2260 3840 share/share-card.png
shot journey-experience.html 2280 6900 journeys/journey-experience-v2.png
shot route-ends.html 1800 1800 journeys/route-ends.png
echo done
