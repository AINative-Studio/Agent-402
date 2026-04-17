#!/usr/bin/env bash
# Repair .ainative, .claude/skills, and .claude/commands symlinks after cloning
# the repo outside the AINative-Studio monorepo.
#
# Refs #282. The symlinks are checked into git with relative paths
# (../core/.ainative, ../../core/.claude/skills, ../../core/.claude/commands)
# that only resolve when the repo sits next to a sibling `core/` checkout.
# This script detects broken symlinks and either:
#   1. Relinks them to a user-specified path (CORE_DIR env var or --core flag)
#   2. Prints clear instructions for manually cloning the core repo
#
# Usage:
#   ./scripts/setup_symlinks.sh [--core /path/to/core]
#   CORE_DIR=/path/to/core ./scripts/setup_symlinks.sh

set -euo pipefail

CORE_DIR="${CORE_DIR:-}"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --core)
      CORE_DIR="$2"
      shift 2
      ;;
    --help|-h)
      grep '^#' "$0" | sed 's/^# \?//'
      exit 0
      ;;
    *)
      echo "Unknown flag: $1" >&2
      exit 1
      ;;
  esac
done

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

# Auto-detect sibling core/ if CORE_DIR not set
if [[ -z "$CORE_DIR" ]]; then
  for candidate in \
    "$(dirname "$REPO_ROOT")/core" \
    "$(dirname "$(dirname "$REPO_ROOT")")/core" \
    "$HOME/core" \
    "$HOME/AINative-Studio/core"; do
    if [[ -d "$candidate/.ainative" && -d "$candidate/.claude/skills" ]]; then
      CORE_DIR="$candidate"
      break
    fi
  done
fi

if [[ -z "$CORE_DIR" ]]; then
  cat >&2 <<'EOF'
Error: could not find an AINative `core/` checkout.

The repo ships `.ainative`, `.claude/skills`, and `.claude/commands` as
symlinks into a sibling `core/` directory containing shared AINative
skills and rules.

Fix: clone the core repo and re-run this script.

  git clone <core-repo-url> /path/to/core
  ./scripts/setup_symlinks.sh --core /path/to/core

Or set CORE_DIR before running:

  CORE_DIR=/path/to/core ./scripts/setup_symlinks.sh
EOF
  exit 1
fi

if [[ ! -d "$CORE_DIR/.ainative" ]]; then
  echo "Error: $CORE_DIR does not contain a .ainative directory" >&2
  exit 1
fi

echo "Using core directory: $CORE_DIR"

link_target() {
  local link_path="$1"
  local target="$2"
  if [[ -L "$link_path" && -e "$link_path" ]]; then
    echo "  OK    $link_path -> $(readlink "$link_path")"
    return
  fi
  if [[ -L "$link_path" || -e "$link_path" ]]; then
    rm -f "$link_path"
  fi
  mkdir -p "$(dirname "$link_path")"
  ln -s "$target" "$link_path"
  echo "  LINK  $link_path -> $target"
}

link_target ".ainative" "$CORE_DIR/.ainative"
link_target ".claude/skills" "$CORE_DIR/.claude/skills"
link_target ".claude/commands" "$CORE_DIR/.claude/commands"

echo
echo "Symlinks resolved. Verify with: ls -la .ainative .claude/skills .claude/commands"
