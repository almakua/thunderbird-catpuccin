#!/usr/bin/env bash
# copies a flavor's userChrome.css and userContent.css into the Thunderbird profile
# usage: ./install.sh <latte|frappe|macchiato|mocha> [--profile <path>]
set -euo pipefail

cd "$(dirname "$0")"

usage() {
  echo "Usage: $0 <latte|frappe|macchiato|mocha> [--profile <profile-path>]" >&2
  exit 1
}

flavor="${1:-}"
case "$flavor" in
  latte|frappe|macchiato|mocha) ;;
  *) usage ;;
esac
shift

profile=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile) profile="${2:-}"; shift 2 ;;
    *) usage ;;
  esac
done

if [[ -z "$profile" ]]; then
  case "$(uname)" in
    Darwin) base="$HOME/Library/Thunderbird" ;;
    *)      base="$HOME/.thunderbird" ;;
  esac
  ini="$base/profiles.ini"
  if [[ ! -f "$ini" ]]; then
    echo "No profiles.ini in $base." >&2
    echo "Start Thunderbird once, or pass the profile with --profile." >&2
    exit 1
  fi
  # the profile really in use is Default= under [Install…]
  # Default=1 under [Profile…] is just the old profile manager fallback
  rel="$(awk -F= '/^\[Install/{s=1;next} /^\[/{s=0} s && $1=="Default"{print $2; exit}' "$ini")"
  if [[ -z "$rel" ]]; then
    rel="$(awk -F= '/^\[Profile/{p="";d=0} $1=="Path"{p=$2} $1=="Default"&&$2=="1"{d=1} d&&p{print p; exit}' "$ini")"
  fi
  [[ -n "$rel" ]] || { echo "Cannot determine profile from $ini: use --profile." >&2; exit 1; }
  case "$rel" in
    /*) profile="$rel" ;;
    *)  profile="$base/$rel" ;;
  esac
fi

[[ -d "$profile" ]] || { echo "Profile not found: $profile" >&2; exit 1; }
[[ -d "dist/$flavor/chrome" ]] || python3 build.py

stamp="$(date +%Y%m%d-%H%M%S)"
mkdir -p "$profile/chrome"
for file in userChrome.css userContent.css; do
  if [[ -f "$profile/chrome/$file" ]]; then
    cp "$profile/chrome/$file" "$profile/chrome/$file.bak-$stamp"
    echo "Backup: chrome/$file.bak-$stamp"
  fi
  cp "dist/$flavor/chrome/$file" "$profile/chrome/$file"
done

# drops any old lines for our prefs from user.js, then appends the generated ones
userjs="$profile/user.js"
if [[ -f "$userjs" ]]; then
  cp "$userjs" "$userjs.bak-$stamp"
  pattern="$(sed -E 's/^user_pref\("([^"]+)".*/\1/' dist/user.js | paste -sd'|' -)"
  grep -vE "user_pref\(\"($pattern)\"" "$userjs.bak-$stamp" > "$userjs" || true
fi
cat dist/user.js >> "$userjs"

echo
echo "Installed Catppuccin $flavor into: $profile"
echo "Next:"
echo "  1. Thunderbird → Add-ons and Themes → gear → Install Add-on From File…"
echo "     and pick dist/catppuccin-$flavor.xpi (skip if already installed)"
echo "  2. Restart Thunderbird."
