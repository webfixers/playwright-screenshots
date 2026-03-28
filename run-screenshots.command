#!/bin/zsh
# Webfixers - combined screenshot launcher
SCRIPT_DIR="${0:A:h}"
cd "$SCRIPT_DIR" || exit 1

if [[ ! -f ".venv/bin/activate" ]]; then
  echo "Missing virtual environment at .venv/bin/activate"
  echo "Press Enter to close..."
  read
  exit 1
fi

if [[ ! -f "screenshot.py" ]]; then
  echo "Missing screenshot.py in: $SCRIPT_DIR"
  echo "Press Enter to close..."
  read
  exit 1
fi

source .venv/bin/activate || exit 1

echo "Screenshot runner"
echo

read "SITEMAP_URL?Enter sitemap URL: "

if [[ -z "$SITEMAP_URL" ]]; then
  echo
  echo "No sitemap URL entered. Press Enter to close..."
  read
  exit 1
fi

echo
echo "Choose variant:"
echo "1) basic"
echo "2) extended"
read "VARIANT_CHOICE?Enter 1 or 2: "

case "$VARIANT_CHOICE" in
  1)
    VARIANT="basic"
    ;;
  2)
    VARIANT="extended"
    ;;
  *)
    echo
    echo "Invalid choice. Press Enter to close..."
    read
    exit 1
    ;;
esac

echo
echo "Running variant: $VARIANT"
echo

python screenshot.py --url "$SITEMAP_URL" --variant "$VARIANT" --generate-index

echo
echo "Done. Press Enter to close..."
read
