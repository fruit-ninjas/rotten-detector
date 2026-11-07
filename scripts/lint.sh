#!/usr/bin/env bash
set -euo pipefail

uv run ruff check src
uv run mypy src
uv run pytest || test $? -eq 5
uv run pre-commit run --all-files