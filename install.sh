#!/usr/bin/env bash

set -euo pipefail

SOURCE=$(cd "$(dirname "$0")" && pwd)
NAME=chinese-skill
MARKER=.chinese-skill-install
operation=install
transport="link"
targets=()
operation_option=
transport_option=

usage() {
  printf '%s\n' \
    "Usage: ./install.sh [claude|codex|opencode ...] [--copy|--link]" \
    "       ./install.sh [targets ...] --status" \
    "       ./install.sh [targets ...] --uninstall" \
    "" \
    "Default: install a symlink for all three agents and add a managed reminder."
}

for argument in "$@"; do
  case "$argument" in
    --copy|--link)
      value=${argument#--}
      if [ -n "$transport_option" ] && [ "$transport_option" != "$value" ]; then
        printf 'Conflicting install methods: --%s and --%s\n' \
          "$transport_option" "$value" >&2
        exit 2
      fi
      transport_option=$value
      transport=$value
      ;;
    --status|--uninstall)
      value=${argument#--}
      if [ -n "$operation_option" ] && [ "$operation_option" != "$value" ]; then
        printf 'Conflicting operations: --%s and --%s\n' \
          "$operation_option" "$value" >&2
        exit 2
      fi
      operation_option=$value
      operation=$value
      ;;
    -h|--help) usage; exit 0 ;;
    claude|codex|opencode) targets+=("$argument") ;;
    *) printf 'Unknown argument: %s\n' "$argument" >&2; exit 2 ;;
  esac
done

if [ "${#targets[@]}" -eq 0 ]; then
  targets=(claude codex opencode)
fi

case "$operation" in
  status|uninstall)
    if [ -n "$transport_option" ]; then
      printf '%s\n' "--copy and --link apply only to installation." >&2
      exit 2
    fi
    ;;
esac

if [ "$operation" = install ]; then
  python3 - "$SOURCE/SKILL.md" "$NAME" <<'PY'
import pathlib
import re
import sys

text = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
parts = text.split("---", 2)
if len(parts) != 3:
    raise SystemExit("SKILL.md has no valid frontmatter block")
match = re.search(r"^name:\s*([^\s]+)\s*$", parts[1], re.M)
if not match or match.group(1) != sys.argv[2]:
    raise SystemExit(f"SKILL.md name must be {sys.argv[2]!r}")
PY
fi

skill_base() {
  case "$1" in
    claude) printf '%s\n' "${CLAUDE_HOME:-$HOME/.claude}/skills" ;;
    codex) printf '%s\n' "${CODEX_HOME:-$HOME/.codex}/skills" ;;
    opencode) printf '%s\n' "${XDG_CONFIG_HOME:-$HOME/.config}/opencode/skills" ;;
  esac
}

instruction_file() {
  case "$1" in
    claude) printf '%s\n' "${CLAUDE_HOME:-$HOME/.claude}/CLAUDE.md" ;;
    codex) printf '%s\n' "${CODEX_HOME:-$HOME/.codex}/AGENTS.md" ;;
    opencode) printf '%s\n' "${XDG_CONFIG_HOME:-$HOME/.config}/opencode/AGENTS.md" ;;
  esac
}

owned() {
  local destination=$1 marker_text
  [ -L "$destination" ] && [ "$(readlink "$destination")" = "$SOURCE" ] && return 0
  [ -f "$destination/$MARKER" ] || return 1
  marker_text=$(cat "$destination/$MARKER")
  [ "$marker_text" = "installer=$NAME
format=copy-v2" ] || [ "$marker_text" = "source=$SOURCE" ]
}

replace_destination() {
  local staged=$1 destination=$2 parent
  LAST_BACKUP=
  parent=$(dirname "$destination")
  if [ -e "$destination" ] || [ -L "$destination" ]; then
    LAST_BACKUP=$(mktemp -d "$parent/.${NAME}.old.XXXXXX")
    rmdir "$LAST_BACKUP"
    mv "$destination" "$LAST_BACKUP"
    if mv "$staged" "$destination"; then
      return 0
    else
      mv "$LAST_BACKUP" "$destination"
      LAST_BACKUP=
      return 1
    fi
  else
    mv "$staged" "$destination"
  fi
}

commit_destination() {
  if [ -n "$LAST_BACKUP" ]; then
    rm -rf "$LAST_BACKUP"
    LAST_BACKUP=
  fi
}

rollback_destination() {
  local destination=$1
  rm -rf "$destination"
  if [ -n "$LAST_BACKUP" ]; then
    mv "$LAST_BACKUP" "$destination"
    LAST_BACKUP=
  fi
}

manage_reminder() {
  local action=$1 file=$2 skill=$3
  python3 - "$action" "$file" "$skill" <<'PY'
import os
import pathlib
import re
import sys
import tempfile

action, raw_path, skill = sys.argv[1:]
path = pathlib.Path(raw_path)
begin = "<!-- chinese-skill:begin -->"
end = "<!-- chinese-skill:end -->"
target = path.resolve(strict=False) if path.is_symlink() else path
pattern = re.compile(rf"{re.escape(begin)}.*?{re.escape(end)}", re.S)
text = target.read_text(encoding="utf-8") if target.exists() else ""
match = pattern.search(text)
if action == "add":
    block = (
        f"{begin}\n"
        f"For every Chinese passage, read `{skill}` before writing or reviewing. "
        "Read it again after context compaction or restoration, a long tool operation, "
        "task switching, and before comments, commits, pull requests, or reviews. "
        "Apply repository instructions first. Ask when an unknown required format "
        f"materially affects the result.\n{end}"
    )
    if match:
        text = pattern.sub(block, text)
    else:
        separator = "\n" if text else ""
        text = f"{text}{separator}{block}\n"
elif match:
    if match.end() == len(text) - 1 and text.endswith("\n"):
        start = match.start() - 1 if match.start() and text[match.start() - 1] == "\n" else match.start()
        text = text[:start]
    else:
        text = text[:match.start()] + text[match.end():]
if not target.exists() and action == "remove":
    raise SystemExit
target.parent.mkdir(parents=True, exist_ok=True)
mode = target.stat().st_mode & 0o777 if target.exists() else 0o644
with tempfile.NamedTemporaryFile(
        "w", dir=target.parent, delete=False, encoding="utf-8") as handle:
    handle.write(text)
    temporary = handle.name
os.chmod(temporary, mode)
os.replace(temporary, target)
PY
}

reminder_current() {
  local file=$1 skill=$2
  python3 - "$file" "$skill" <<'PY'
import pathlib
import sys

raw_path, skill = sys.argv[1:]
path = pathlib.Path(raw_path)
target = path.resolve(strict=False) if path.is_symlink() else path
if not target.is_file():
    raise SystemExit(1)
begin = "<!-- chinese-skill:begin -->"
end = "<!-- chinese-skill:end -->"
block = (
    f"{begin}\n"
    f"For every Chinese passage, read `{skill}` before writing or reviewing. "
    "Read it again after context compaction or restoration, a long tool operation, "
    "task switching, and before comments, commits, pull requests, or reviews. "
    "Apply repository instructions first. Ask when an unknown required format "
    f"materially affects the result.\n{end}"
)
text = target.read_text(encoding="utf-8")
valid = text.count(block) == 1 and text.count(begin) == 1 and text.count(end) == 1
raise SystemExit(0 if valid else 1)
PY
}

copy_current() {
  python3 - "$1" "$2" "$MARKER" <<'PY'
import hashlib
import os
import pathlib
import stat
import sys

source, destination = map(pathlib.Path, sys.argv[1:3])
marker = sys.argv[3]
ignored = {".git", ".hg", ".svn", ".github", "__pycache__"}


def inventory(root):
    entries = {}
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if set(relative.parts).intersection(ignored):
            continue
        if path.name == marker or path.suffix in {".pyc", ".pyo"}:
            continue
        if path.is_symlink():
            entries[str(relative)] = ("link", os.readlink(path))
        elif path.is_file():
            mode = stat.S_IMODE(path.stat().st_mode)
            entries[str(relative)] = ("file", mode, hashlib.sha256(path.read_bytes()).digest())
        elif path.is_dir():
            entries[str(relative)] = ("directory",)
    return entries


raise SystemExit(0 if inventory(source) == inventory(destination) else 1)
PY
}

status=0
for agent in "${targets[@]}"; do
  base=$(skill_base "$agent")
  destination="$base/$NAME"
  instructions=$(instruction_file "$agent")

  if [ "$operation" = status ]; then
    if [ -L "$destination" ] && [ "$(readlink "$destination")" = "$SOURCE" ]; then
      state="link, current"
    elif [ -d "$destination" ] && owned "$destination"; then
      if copy_current "$SOURCE" "$destination"; then
        state="copy, current"
      else
        state="copy, stale"
        status=1
      fi
    elif [ -e "$destination" ] || [ -L "$destination" ]; then
      state="unowned"
      status=1
    else
      state="not installed"
      status=1
    fi
    if reminder_current "$instructions" "$destination/SKILL.md"; then
      reminder="reminder present"
    else
      reminder="reminder absent"
      status=1
    fi
    printf '%-9s %-16s %s; %s\n' "$agent" "$state" "$destination" "$reminder"
    continue
  fi

  if [ "$operation" = uninstall ]; then
    if [ -e "$destination" ] || [ -L "$destination" ]; then
      if owned "$destination"; then
        rm -rf "$destination"
        printf '%-9s removed %s\n' "$agent" "$destination"
      else
        printf '%-9s refused: %s is not owned by this installer\n' "$agent" "$destination" >&2
        status=1
      fi
    else
      printf '%-9s not installed\n' "$agent"
    fi
    manage_reminder remove "$instructions" "$destination/SKILL.md"
    continue
  fi

  mkdir -p "$base"
  if { [ -e "$destination" ] || [ -L "$destination" ]; } && ! owned "$destination"; then
    printf '%-9s refused: %s is not owned by this installer\n' "$agent" "$destination" >&2
    status=1
    continue
  fi

  if [ "$transport" = link ]; then
    stage_parent=$(mktemp -d "$base/.${NAME}.new.XXXXXX")
    stage="$stage_parent/$NAME"
    ln -s "$SOURCE" "$stage"
    replace_destination "$stage" "$destination"
    rmdir "$stage_parent"
  else
    stage=$(mktemp -d "$base/.${NAME}.new.XXXXXX")
    python3 - "$SOURCE" "$stage" <<'PY'
import pathlib
import shutil
import sys

source, destination = map(pathlib.Path, sys.argv[1:])
shutil.copytree(
    source,
    destination,
    dirs_exist_ok=True,
    symlinks=True,
    ignore=shutil.ignore_patterns(
        ".git", ".hg", ".svn", ".github", "__pycache__", "*.pyc", "*.pyo"),
)
PY
    printf 'installer=%s\nformat=copy-v2\n' "$NAME" >"$stage/$MARKER"
    replace_destination "$stage" "$destination"
  fi
  if ! manage_reminder add "$instructions" "$destination/SKILL.md"; then
    rollback_destination "$destination"
    printf '%-9s failed to update %s; installation rolled back\n' "$agent" "$instructions" >&2
    status=1
    continue
  fi
  commit_destination
  printf '%-9s %-6s %s\n' "$agent" "$transport" "$destination"
done

exit "$status"
