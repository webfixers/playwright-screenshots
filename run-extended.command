#!/bin/zsh
# Webfixers - extended screenshot launcher
cd "/Users/mennofink/Library/CloudStorage/GoogleDrive-menno@webfixers.nl/.shortcut-targets-by-id/1snrUQNe2fCBN9HocLIwfJVuVQU4AE_2x/Development/Applicaties/playwright-screenshots" || exit 1
source .venv/bin/activate || exit 1

read "SITEMAP_URL?Enter sitemap URL: "
echo
python screenshot.py --url "$SITEMAP_URL" --variant extended --generate-index

echo
echo "Done. Press Enter to close..."
read
