#!/bin/zsh
# Webfixers - GUI screenshot launcher
SCRIPT_DIR="${0:A:h}"
cd "$SCRIPT_DIR" || exit 1

if [[ ! -x "/usr/bin/python3" ]]; then
  echo "Missing macOS system Python at /usr/bin/python3"
  echo "Press Enter to close..."
  read
  exit 1
fi

if [[ ! -f "gui.py" ]]; then
  echo "Missing gui.py in: $SCRIPT_DIR"
  echo "Press Enter to close..."
  read
  exit 1
fi

/usr/bin/python3 gui.py
