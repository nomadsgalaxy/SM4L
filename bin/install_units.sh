#!/usr/bin/env bash
# Install the SM4L systemd user units for THIS checkout: render the templates in units/ (@SM4L_ROOT@ becomes this
# checkout's path), write them to ~/.config/systemd/user, remove stale sm4l-*.service files, reload systemd and enable
# the units. Nothing is started or restarted unless you ask: close CAD first, then use --restart to move running units
# to the new paths.
# Usage: install_units.sh [--dest DIR] [--no-systemctl] [--restart] [--register-paths]
#   --dest DIR        write the rendered units here instead of ~/.config/systemd/user (used by the test)
#   --no-systemctl    only render and remove; never call systemctl
#   --restart         restart the units that are running (stop CAD first)
#   --register-paths  also run bin/register_paths.py (application menu entry and the prefix's WineBrowser value)
set -euo pipefail
root="$(realpath -- "$(dirname -- "$(realpath -- "$0")")/..")"
dest="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
systemctl_on=1 restart=0 register=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dest) dest="$2"; shift ;;
    --no-systemctl) systemctl_on=0 ;;
    --restart) restart=1 ;;
    --register-paths) register=1 ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
  shift
done
case "$root" in *$'\n'*|*'"'*|*'\'*) echo "The checkout path must not contain a newline, a double quote or a backslash: $root" >&2; exit 2 ;; esac
# systemd expands % and $ in ExecStart: double them. sed needs & and | escaped in the replacement.
value="${root//%/%%}"; value="${value//\$/\$\$}"; value="${value//\\/\\\\}"; value="${value//&/\\&}"; value="${value//|/\\|}"
mkdir -p "$dest"
templates=()
for template in "$root"/units/sm4l-*.service; do
  name="$(basename -- "$template")"; templates+=("$name")
  sed "s|@SM4L_ROOT@|$value|g" "$template" > "$dest/$name.new"
  if grep -q '@SM4L_ROOT@' "$dest/$name.new"; then echo "Unreplaced placeholder in $name" >&2; rm -f "$dest/$name.new"; exit 1; fi
  mv -- "$dest/$name.new" "$dest/$name"
  echo "installed $dest/$name"
done
for old in "$dest"/sm4l-*.service; do
  [[ -e "$old" ]] || continue
  name="$(basename -- "$old")"
  if [[ ! " ${templates[*]} " == *" $name "* ]]; then
    if [[ "$systemctl_on" == 1 ]]; then systemctl --user disable --now "$name" 2>/dev/null || true; fi
    rm -f -- "$old"; echo "removed stale $name"
  fi
done
if [[ "$systemctl_on" == 1 ]]; then
  systemctl --user daemon-reload
  for name in "${templates[@]}"; do systemctl --user enable "$name" 2>&1 | tail -1 || true; done
  if [[ "$restart" == 1 ]]; then
    for name in "${templates[@]}"; do
      if systemctl --user is-active --quiet "$name"; then systemctl --user restart "$name"; echo "restarted $name"; fi
    done
  else
    echo "Running units keep their old paths until they restart (close CAD, then: $0 --restart)."
  fi
fi
if [[ "$register" == 1 ]]; then python3 "$root/bin/register_paths.py"; fi
