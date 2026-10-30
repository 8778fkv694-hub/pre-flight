#!/bin/sh
# 起飞 Pre-flight — host-neutral project checks.
# Copy to <project>/scripts/ci-check.sh. Run locally or from any CI:
#   sh scripts/ci-check.sh            (from the project root)
#   sh /path/to/project/scripts/ci-check.sh   (from anywhere; the script locates the project)
# Exit 0 = pass (warnings allowed), 1 = failure, 2 = cannot run.
# This script is a guardrail, not an enforced security mechanism.
set -u

script_dir=$(CDPATH= cd -- "$(dirname "$0")" && pwd) || exit 2
root=$(CDPATH= cd -- "$script_dir/.." && pwd) || exit 2
cd "$root" || exit 2

fail=0
warn() { printf 'WARN: %s\n' "$*"; }
bad() { printf 'FAIL: %s\n' "$*"; fail=1; }

# 1) Protected basic-law clauses (only when the project adopted the checker).
if [ -f AGENT.md ]; then
    if [ -f scripts/check_basic_law.py ]; then
        if [ -f docs/sdlc/maintain/basic-law.lock.json ]; then
            if command -v python3 >/dev/null 2>&1; then
                python3 scripts/check_basic_law.py --project "$root" || fail=1
            else
                warn "未找到 python3；无法检查受保护条款"
            fi
        else
            warn "基本法哈希基线尚未冻结；人确认后运行 scripts/check_basic_law.py --freeze --note <原因>"
        fi
    else
        warn "未找到 scripts/check_basic_law.py；跳过受保护条款检查（如已采用，从技能包复制）"
    fi
else
    warn "未找到 AGENT.md；跳过基本法检查"
fi

# 1b) Detect basic-law lock/checker modifications (prevent silent agent self-amendment).
if command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    touched_guard=""
    status_guard=$(git status --porcelain -- \
        docs/sdlc/maintain/basic-law.lock.json \
        scripts/check_basic_law.py \
        scripts/ci-check.sh 2>/dev/null || true)
    if [ -n "$status_guard" ]; then
        touched_guard="$status_guard"
    elif [ -n "${CI_BASE_REF:-}" ]; then
        diff_guard=$(git diff --name-status "${CI_BASE_REF}...HEAD" -- \
            docs/sdlc/maintain/basic-law.lock.json \
            scripts/check_basic_law.py \
            scripts/ci-check.sh 2>/dev/null || true)
        if [ -n "$diff_guard" ]; then
            touched_guard="$diff_guard"
        fi
    fi
    if [ -n "$touched_guard" ]; then
        warn "AMENDMENT_TOUCHED: 检测到基本法哈希锁或检查脚本变更，须由人逐条核对修正案记录（防 Agent 自写日志并自跑 --force --amend）"
        if [ "${CI_REQUIRE_AMEND_ACK:-0}" = "1" ] && [ "${CI_AMEND_APPROVED:-0}" != "1" ]; then
            bad "AMENDMENT_TOUCHED: CI_REQUIRE_AMEND_ACK=1 已启用但未设置 CI_AMEND_APPROVED=1；基本法锁或门禁脚本变更须经人显式放行"
        fi
    fi
fi

# 2) Unresolved template placeholders in Markdown.
if find . -path ./.git -prune -o -type f -name '*.md' -exec \
    grep -l '{{[A-Za-z_][A-Za-z0-9_]*}}' {} + 2>/dev/null | grep -q .; then
    bad "发现未替换的模板占位符 ({{...}})；可能是未完成初始化的资料"
fi

# 3) Minimal secret-pattern scan (high false-negative and false-positive risk).
if find . \( -path ./.git -o -path ./node_modules -o -path ./.venv \
    -o -path ./venv -o -path ./dist -o -path ./build \) -prune -o -type f -exec \
    grep -IlnE \
    -e '-----BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----' \
    -e 'AKIA[0-9A-Z]{16}' \
    -e 'gh[pousr]_[A-Za-z0-9]{36,}' \
    -e 'sk-[A-Za-z0-9]{20,}' \
    {} + 2>/dev/null | grep -q .; then
    bad "发现疑似密钥材料（私钥头/云密钥/token 形态）；请核对并移除，勿提交"
fi

# 4) Optional project-specific checks.
if [ -f scripts/project-check.sh ]; then
    sh scripts/project-check.sh || fail=1
fi

if [ "$fail" -eq 0 ]; then
    echo "ci-check: PASS"
else
    echo "ci-check: FAIL"
fi
exit "$fail"
