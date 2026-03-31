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
ICON_SOURCE_FILE="$SCRIPT_DIR/macos-app/GenerateAppIcon.m"
ICON_PACKER_SCRIPT="$SCRIPT_DIR/macos-app/build_icns.py"
PLIST_FILE="$SCRIPT_DIR/macos-app/Info.plist"
EXECUTABLE_PATH="$MACOS_DIR/$EXECUTABLE_NAME"
ICON_TOOL_PATH="$BUILD_DIR/GenerateAppIcon"
ICON_PNG_PATH="$BUILD_DIR/AppIcon-1024.png"
ICONSET_DIR="$BUILD_DIR/AppIcon.iconset"
ICON_ICNS_PATH="$RESOURCES_DIR/AppIcon.icns"

rm -rf "$APP_DIR"
rm -rf "$ICONSET_DIR"
mkdir -p "$MACOS_DIR" "$RESOURCES_DIR"

if [[ ! -f "$SOURCE_FILE" ]]; then
  echo "Missing source file: $SOURCE_FILE"
  exit 1
fi

if [[ ! -f "$PLIST_FILE" ]]; then
  echo "Missing Info.plist: $PLIST_FILE"
  exit 1
fi

if [[ ! -f "$ICON_SOURCE_FILE" ]]; then
  echo "Missing icon source file: $ICON_SOURCE_FILE"
  exit 1
fi

if [[ ! -f "$ICON_PACKER_SCRIPT" ]]; then
  echo "Missing icon packer script: $ICON_PACKER_SCRIPT"
  exit 1
fi

clang -fobjc-arc -framework Cocoa "$SOURCE_FILE" -o "$EXECUTABLE_PATH"
clang -fobjc-arc -framework Cocoa "$ICON_SOURCE_FILE" -o "$ICON_TOOL_PATH"
"$ICON_TOOL_PATH" "$ICON_PNG_PATH"

mkdir -p "$ICONSET_DIR"
sips -z 16 16 "$ICON_PNG_PATH" --out "$ICONSET_DIR/icon_16x16.png" >/dev/null
sips -z 32 32 "$ICON_PNG_PATH" --out "$ICONSET_DIR/icon_16x16@2x.png" >/dev/null
sips -z 32 32 "$ICON_PNG_PATH" --out "$ICONSET_DIR/icon_32x32.png" >/dev/null
sips -z 64 64 "$ICON_PNG_PATH" --out "$ICONSET_DIR/icon_32x32@2x.png" >/dev/null
sips -z 128 128 "$ICON_PNG_PATH" --out "$ICONSET_DIR/icon_128x128.png" >/dev/null
sips -z 256 256 "$ICON_PNG_PATH" --out "$ICONSET_DIR/icon_128x128@2x.png" >/dev/null
sips -z 256 256 "$ICON_PNG_PATH" --out "$ICONSET_DIR/icon_256x256.png" >/dev/null
sips -z 512 512 "$ICON_PNG_PATH" --out "$ICONSET_DIR/icon_256x256@2x.png" >/dev/null
sips -z 512 512 "$ICON_PNG_PATH" --out "$ICONSET_DIR/icon_512x512.png" >/dev/null
sips -z 1024 1024 "$ICON_PNG_PATH" --out "$ICONSET_DIR/icon_512x512@2x.png" >/dev/null
/usr/bin/python3 "$ICON_PACKER_SCRIPT" "$ICONSET_DIR" "$ICON_ICNS_PATH"

cp "$PLIST_FILE" "$APP_DIR/Contents/Info.plist"
touch "$APP_DIR"

echo "Built app:"
echo "$APP_DIR"
echo
echo "You can now double-click the app in Finder."
