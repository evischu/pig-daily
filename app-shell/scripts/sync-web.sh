#!/usr/bin/env bash
# Pulls the latest web app into the Capacitor wrapper's www/ folder.
# Run this before `npx cap sync ios` any time calendar-app/ changes —
# app-shell/www is a build artifact, never edited directly.
set -euo pipefail
cd "$(dirname "$0")/.."
rm -rf www
mkdir -p www
cp ../calendar-app/index.html ../calendar-app/config.js ../calendar-app/manifest.webmanifest \
   ../calendar-app/icon-192.png ../calendar-app/icon-512.png ../calendar-app/icon-maskable.png \
   ../calendar-app/apple-touch-icon.png www/
# sw.js is a PWA-only concern (browser caching); the native wrapper's own
# WebView doesn't need it and Capacitor's local-file serving doesn't
# benefit from a service worker the way a real HTTPS origin does.
echo "synced into app-shell/www"
