#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
APP_NAME="Playwright Screenshots"
BUILD_DIR="$SCRIPT_DIR/build"
APP_DIR="$BUILD_DIR/$APP_NAME.app"
MACOS_DIR="$APP_DIR/Contents/MacOS"
RESOURCES_DIR="$APP_DIR/Contents/Resources"
EXECUTABLE_NAME="PlaywrightScreenshotsLauncher"
SOURCE_FILE="$SCRIPT_DIR/macos-app/PlaywrightScreenshotsLauncher.m"
PLIST_FILE="$SCRIPT_DIR/macos-app/Info.plist"
EXECUTABLE_PATH="$MACOS_DIR/$EXECUTABLE_NAME"

mkdir -p "$MACOS_DIR" "$RESOURCES_DIR"

if [[ ! -f "$SOURCE_FILE" ]]; then
  echo "Missing source file: $SOURCE_FILE"
  exit 1
fi

if [[ ! -f "$PLIST_FILE" ]]; then
  echo "Missing Info.plist: $PLIST_FILE"
  exit 1
fi

clang -fobjc-arc -framework Cocoa "$SOURCE_FILE" -o "$EXECUTABLE_PATH"
cp "$PLIST_FILE" "$APP_DIR/Contents/Info.plist"

echo "Built app:"
echo "$APP_DIR"
echo
echo "You can now double-click the app in Finder."
