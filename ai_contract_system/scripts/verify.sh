#!/usr/bin/env bash

set -euo pipefail

echo "========================================"
echo " Running verification"
echo "========================================"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$ROOT_DIR"

FAILURES=0

run_step() {
  local description="$1"
  shift
  echo ""
  echo "→ $description"
  if "$@"; then
    echo "✓ Passed: $description"
  else
    echo "✗ Failed: $description"
    FAILURES=$((FAILURES + 1))
  fi
}

# ---------------------------------------------------------------------------
# Contract checks
# ---------------------------------------------------------------------------

run_step "Check required contract files exist" \
  test -f CLAUDE.md \
  && test -f docs/workflow.md \
  && test -f docs/assumptions.md \
  && test -f docs/decisions.md \
  && test -f docs/glossary.md

# ---------------------------------------------------------------------------
# Git hygiene (non-destructive)
# ---------------------------------------------------------------------------

if command -v git >/dev/null 2>&1; then
  run_step "Check git working tree is clean" \
    test -z "$(git status --porcelain)"
else
  echo "→ Git not available, skipping git checks"
fi

# ---------------------------------------------------------------------------
# Language / project-specific hooks
# (intentionally empty by default)
# ---------------------------------------------------------------------------

# Example hooks (uncomment when applicable):
# run_step "Run tests" pytest
# run_step "Run linter" ruff check .
# run_step "Type checking" mypy .

# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------

echo ""
if [ "$FAILURES" -eq 0 ]; then
  echo "========================================"
  echo " Verification PASSED"
  echo "========================================"
  exit 0
else
  echo "========================================"
  echo " Verification FAILED ($FAILURES failures)"
  echo "========================================"
  exit 1
fi
