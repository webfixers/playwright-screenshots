#!/bin/zsh
# Webfixers - combined screenshot launcher
cd "/Users/mennofink/Library/CloudStorage/GoogleDrive-menno@webfixers.nl/.shortcut-targets-by-id/1snrUQNe2fCBN9HocLIwfJVuVQU4AE_2x/Development/Applicaties/playwright-screenshots" || exit 1
source .venv/bin/activate || exit 1

echo "Screenshot runner"
echo

read "SITEMAP_URL?Enter sitemap URL: "
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
