#!/usr/bin/env bash
set -euo pipefail

[[ -z "${1:-}" || -z "${2:-}" ]] && printf 'usage: dedup.sh <operation> <root_dir>\n' >&2 && exit 1

uv run rotten-dedup "$1" "$2"
