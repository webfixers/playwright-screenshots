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

echo "Choose input mode:"
echo "1) single website"
echo "2) website list file"
read "INPUT_MODE_CHOICE?Enter 1 or 2 [1]: "

case "$INPUT_MODE_CHOICE" in
  ""|1)
    INPUT_MODE="single"
    ;;
  2)
    INPUT_MODE="file"
    ;;
  *)
    echo
    echo "Invalid choice. Press Enter to close..."
    read
    exit 1
    ;;
esac

echo
if [[ "$INPUT_MODE" == "single" ]]; then
  read "SITEMAP_URL?Enter website or sitemap (for example example.com or example.com/sitemap.xml): "
else
  read "URL_FILE?Enter path to website list file: "
fi

if [[ "$INPUT_MODE" == "single" ]] && [[ -z "$SITEMAP_URL" ]]; then
  echo
  echo "No website entered. Press Enter to close..."
  read
  exit 1
fi

if [[ "$INPUT_MODE" == "file" ]]; then
  if [[ -z "$URL_FILE" ]]; then
    echo
    echo "No list file entered. Press Enter to close..."
    read
    exit 1
  fi
  if [[ ! -f "$URL_FILE" ]]; then
    echo
    echo "List file not found: $URL_FILE"
    echo "Press Enter to close..."
    read
    exit 1
  fi
fi

echo
echo "Choose variant:"
echo "1) basic"
echo "2) extended"
read "VARIANT_CHOICE?Enter 1 or 2 [1]: "

case "$VARIANT_CHOICE" in
  ""|1)
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
echo "Rerun only previously failed URLs?"
echo "1) no"
echo "2) yes"
read "ONLY_FAILED_CHOICE?Enter 1 or 2 [1]: "

case "$ONLY_FAILED_CHOICE" in
  ""|1)
    ONLY_FAILED="false"
    ;;
  2)
    ONLY_FAILED="true"
    ;;
  *)
    echo
    echo "Invalid choice. Press Enter to close..."
    read
    exit 1
    ;;
esac

echo
read "INCLUDE_FILTERS?Optional include path fragments (comma-separated, blank = all): "
echo
read "EXCLUDE_FILTERS?Optional exclude path fragments (comma-separated, blank = none): "
echo
read "MAX_URLS?Optional max URLs to process (blank = all): "

if [[ -n "$MAX_URLS" ]]; then
  if [[ ! "$MAX_URLS" =~ ^[0-9]+$ ]] || [[ "$MAX_URLS" == "0" ]]; then
    echo
    echo "Max URLs must be a positive whole number. Press Enter to close..."
    read
    exit 1
  fi
fi

echo
echo "Choose timeout profile:"
echo "1) normal"
echo "2) slow"
read "TIMEOUT_PROFILE_CHOICE?Enter 1 or 2 [1]: "

case "$TIMEOUT_PROFILE_CHOICE" in
  ""|1)
    TIMEOUT_PROFILE="normal"
    ;;
  2)
    TIMEOUT_PROFILE="slow"
    ;;
  *)
    echo
    echo "Invalid choice. Press Enter to close..."
    read
    exit 1
    ;;
esac

echo
echo "Open output automatically after the run?"
echo "1) yes"
echo "2) no"
read "OPEN_OUTPUT_CHOICE?Enter 1 or 2 [1]: "

case "$OPEN_OUTPUT_CHOICE" in
  ""|1)
    NO_OPEN="false"
    ;;
  2)
    NO_OPEN="true"
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
echo "Only failed: $ONLY_FAILED"
echo "Input mode: $INPUT_MODE"

if [[ "$INPUT_MODE" == "single" ]]; then
  echo "Website input: $SITEMAP_URL"
else
  echo "List file: $URL_FILE"
fi

if [[ -n "$INCLUDE_FILTERS" ]]; then
  echo "Include filters: $INCLUDE_FILTERS"
fi

if [[ -n "$EXCLUDE_FILTERS" ]]; then
  echo "Exclude filters: $EXCLUDE_FILTERS"
fi

if [[ -n "$MAX_URLS" ]]; then
  echo "Max URLs: $MAX_URLS"
fi

echo "Timeout profile: $TIMEOUT_PROFILE"

echo

COMMAND=(python screenshot.py --variant "$VARIANT" --generate-index)

if [[ "$INPUT_MODE" == "single" ]]; then
  COMMAND+=(--url "$SITEMAP_URL")
else
  COMMAND+=(--url-file "$URL_FILE")
fi

if [[ "$ONLY_FAILED" == "true" ]]; then
  COMMAND+=(--only-failed)
fi

if [[ -n "$INCLUDE_FILTERS" ]]; then
  COMMAND+=(--include "$INCLUDE_FILTERS")
fi

if [[ -n "$EXCLUDE_FILTERS" ]]; then
  COMMAND+=(--exclude "$EXCLUDE_FILTERS")
fi

if [[ -n "$MAX_URLS" ]]; then
  COMMAND+=(--max-urls "$MAX_URLS")
fi

COMMAND+=(--timeout-profile "$TIMEOUT_PROFILE")

if [[ "$NO_OPEN" == "true" ]]; then
  COMMAND+=(--no-open)
fi

"${COMMAND[@]}"

echo
echo "Done. Press Enter to close..."
read
