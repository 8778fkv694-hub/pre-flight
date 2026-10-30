#!/bin/sh
# 起飞 Pre-flight — optional local pre-commit gate (host-neutral).
# Install: cp this file to <repo>/.git/hooks/pre-commit && chmod +x <repo>/.git/hooks/pre-commit
# It calls <repo>/scripts/ci-check.sh if present. A local hook can be bypassed
# with "git commit --no-verify"; it is a guardrail, not an enforced gate.
set -u

root=$(git rev-parse --show-toplevel 2>/dev/null)
if [ -z "${root:-}" ]; then
    hook_dir=$(CDPATH= cd -- "$(dirname "$0")" && pwd) || exit 0
    root=$(CDPATH= cd -- "$hook_dir/../.." && pwd) || exit 0
fi
cd "$root" || exit 0

if [ ! -f scripts/ci-check.sh ]; then
    echo "pre-commit: scripts/ci-check.sh not found; skipping project checks."
    echo "pre-commit: copy assets/ci/ci-check.sh from the Pre-flight skill to enable them."
    exit 0
fi

if sh scripts/ci-check.sh; then
    exit 0
fi

echo "pre-commit: checks failed. Fix the issues, or bypass explicitly with"
echo "pre-commit: 'git commit --no-verify' (a bypass is not a review)."
exit 1
