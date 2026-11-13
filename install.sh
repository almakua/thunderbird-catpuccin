#!/usr/bin/env bash
# Installa userChrome.css / userContent.css di un flavor nel profilo Thunderbird.
# Uso: ./install.sh <latte|frappe|macchiato|mocha> [--profile <percorso>]
set -euo pipefail

cd "$(dirname "$0")"

usage() {
  echo "Uso: $0 <latte|frappe|macchiato|mocha> [--profile <percorso-profilo>]" >&2
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
    echo "Nessun profiles.ini in $base." >&2
    echo "Avvia Thunderbird almeno una volta, oppure indica il profilo con --profile." >&2
    exit 1
  fi
  # Il profilo realmente usato è il Default= della sezione [Install…];
  # il Default=1 delle sezioni [Profile…] è solo il fallback del vecchio profile manager.
  rel="$(awk -F= '/^\[Install/{s=1;next} /^\[/{s=0} s && $1=="Default"{print $2; exit}' "$ini")"
  if [[ -z "$rel" ]]; then
    rel="$(awk -F= '/^\[Profile/{p="";d=0} $1=="Path"{p=$2} $1=="Default"&&$2=="1"{d=1} d&&p{print p; exit}' "$ini")"
  fi
  [[ -n "$rel" ]] || { echo "Impossibile capire il profilo da $ini: usa --profile." >&2; exit 1; }
  case "$rel" in
    /*) profile="$rel" ;;
    *)  profile="$base/$rel" ;;
  esac
fi

[[ -d "$profile" ]] || { echo "Profilo non trovato: $profile" >&2; exit 1; }
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

# Aggiorna user.js: rimuove le righe delle stesse preferenze, poi aggiunge quelle generate.
userjs="$profile/user.js"
if [[ -f "$userjs" ]]; then
  cp "$userjs" "$userjs.bak-$stamp"
  pattern="$(sed -E 's/^user_pref\("([^"]+)".*/\1/' dist/user.js | paste -sd'|' -)"
  grep -vE "user_pref\(\"($pattern)\"" "$userjs.bak-$stamp" > "$userjs" || true
fi
cat dist/user.js >> "$userjs"

echo
echo "Installato Catppuccin $flavor in: $profile"
echo "Ora:"
echo "  1. Thunderbird → Componenti aggiuntivi e temi → ingranaggio → Installa componente aggiuntivo da file…"
echo "     e scegli dist/catppuccin-$flavor.xpi"
echo "  2. Riavvia Thunderbird."
