#!/usr/bin/env bash
# Run a STABLE copy of the dashboard from a separate worktree that tracks origin/main (default port 8502).
# The main folder shows whatever branch is checked out there (agents switch branches), so this gives a view that only changes when main changes.
#   scripts/run_stable.sh            # start (creates ../lebanon-hhc-main on first run, updates it to origin/main)
#   STABLE_BRANCH=shreya/some-branch STABLE_PORT=8503 scripts/run_stable.sh   # pin a different ref
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WT="${STABLE_DIR:-$REPO/../lebanon-hhc-main}"
REF="${STABLE_BRANCH:-main}"
PORT="${STABLE_PORT:-8502}"
git -C "$REPO" fetch -q origin
if [ ! -d "$WT" ]; then
  git -C "$REPO" worktree add --detach "$WT" "origin/$REF"      # detached: never conflicts with a branch checked out elsewhere
else
  git -C "$WT" checkout -q --detach "origin/$REF"
fi
echo "Stable app: $(git -C "$WT" log --oneline -1)"
cd "$WT"
# PYTHONPATH makes this worktree's src win over the editable install that points at the main folder
PYTHONPATH="$WT/src" BEQAA_DATA="${BEQAA_DATA:-auto}" exec "$REPO/.venv/bin/streamlit" run app/streamlit_app.py --server.port "$PORT" --server.headless true --server.runOnSave false
