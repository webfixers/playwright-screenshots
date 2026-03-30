#!/bin/zsh
# Webfixers - GUI screenshot launcher
SCRIPT_DIR="${0:A:h}"
cd "$SCRIPT_DIR" || exit 1

if [[ ! -f ".venv/bin/activate" ]]; then
  echo "Missing virtual environment at .venv/bin/activate"
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

source .venv/bin/activate || exit 1
python gui.py
