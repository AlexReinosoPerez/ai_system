#!/usr/bin/env bash

set -euo pipefail

echo "========================================"
echo " Initializing claude_system"
echo "========================================"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

create_dir() {
  local dir="$1"
  if [ ! -d "$dir" ]; then
    mkdir -p "$dir"
    echo "✓ Created directory: $dir"
  else
    echo "• Directory exists: $dir"
  fi
}

create_file() {
  local file="$1"
  local content="$2"
  if [ ! -f "$file" ]; then
    echo "$content" > "$file"
    echo "✓ Created file: $file"
  else
    echo "• File exists: $file"
  fi
}

# ---------------------------------------------------------------------------
# Directories
# ---------------------------------------------------------------------------

create_dir "docs"
create_dir "prompts"
create_dir "ai/memory"
create_dir "ai/sessions"
create_dir "scripts"
create_dir ".github/workflows"

# ---------------------------------------------------------------------------
# Core contract files
# ---------------------------------------------------------------------------

create_file "README.md" "# Claude System

See CLAUDE.md for the authoritative contract.
"

create_file "CLAUDE.md" "# Placeholder

Run init.sh from the repository root after copying claude_system.
"

# ---------------------------------------------------------------------------
# Docs
# ---------------------------------------------------------------------------

create_file "docs/workflow.md" "# Workflow

Defined in claude_system/docs/workflow.md
"

create_file "docs/assumptions.md" "# Assumptions

Defined in claude_system/docs/assumptions.md
"

create_file "docs/decisions.md" "# Decisions

Defined in claude_system/docs/decisions.md
"

create_file "docs/glossary.md" "# Glossary

Defined in claude_system/docs/glossary.md
"

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

create_file "prompts/architect.md" "# Architect prompt"
create_file "prompts/implementer.md" "# Implementer prompt"
create_file "prompts/reviewer.md" "# Reviewer prompt"
create_file "prompts/verifier.md" "# Verifier prompt"
create_file "prompts/handoff_claude_to_copilot.md" "# Claude → Copilot handoff"
create_file "prompts/handoff_copilot_to_claude.md" "# Copilot → Claude escalation"
create_file "prompts/session_close.md" "# Session close prompt"

# ---------------------------------------------------------------------------
# AI memory placeholders
# ---------------------------------------------------------------------------

create_file "ai/memory/README.md" "# Curated AI Memory

Only intentional, reviewed knowledge belongs here.
"

create_file "ai/sessions/README.md" "# AI Sessions

Summaries of completed sessions live here.
"

# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

if [ ! -f "scripts/verify.sh" ]; then
  cat <<'EOF' > scripts/verify.sh
#!/usr/bin/env bash
set -euo pipefail
echo "Verification placeholder. Replace with project-specific checks."
EOF
  chmod +x scripts/verify.sh
  echo "✓ Created scripts/verify.sh"
else
  echo "• scripts/verify.sh exists"
fi

# ---------------------------------------------------------------------------
# CI
# ---------------------------------------------------------------------------

create_file ".github/workflows/verify.yml" "name: verify
on: [push, pull_request]
jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: chmod +x scripts/verify.sh
      - run: scripts/verify.sh
"

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------

echo ""
echo "========================================"
echo " claude_system initialization complete"
echo "========================================"
echo ""
echo "Next steps:"
echo "1. Review and replace placeholder files with full versions"
echo "2. Commit the initialized structure"
echo "3. Customize scripts/verify.sh for your project"
