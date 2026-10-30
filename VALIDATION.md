# Validation / 验证

2026-10-29。Skill frontmatter validator: PASS.

- PASS: dry-run creates no files
- PASS: applied 8 templates and 3 adapters; placeholders resolved
- PASS: non-empty target refused without changes
- PASS: generated project links resolve
- PASS: no-adapter mode works
- PASS: unknown adapter rejected before writes
- PASS: symlink target refused
- PASS: package local Markdown links resolve

初始化行为在临时目录实测；未调用模型、部署、安装或写入真实项目。未进行跨客户端真实Agent行为/自动发现的端到端验证；这些结果不能证明模型一定遵守流程。

Initialization behavior was tested in temporary directories. No model calls, deployment, installation, or existing-project writes. Cross-client agent behavior and automatic discovery have not been tested end to end.

## 2026-10-29 reference and onboarding revision

- PASS: repeated initializer checks after template changes, including draft basic law, absent confirmation record, and unconfirmed Spec state. These inspect document output, not agent behavior.
- PASS: separate Chinese/English README pages, reciprocal language links, package and generated local links.
- PASS: skill frontmatter validator and whitespace check.
- Reviewed: both provided references mapped to workflow/templates; the explicit AI-restatement → human-confirmation requirement is reflected in skill, lifecycle, versioning, template and both README pages.

未进行真实模型对“模糊输入/修改后重确认/已有确认接续”等场景的行为评测；文档指导不能保证宿主执行。未新增或宣称存在CI、运行时强制门禁或自动发布能力。

## 2026-10-30 mid-run supplement rule

- Confirmed: originator confirmed the AI restatement of the mid-run supplement rule (four-type triage) and chose formal inclusion in the skill before any file change. Confirmation came from the originator's reply in session, not from an agent or generated file.
- Corrected after an independent read-only review: the first version had inconsistent labels across summaries, an ambiguous "keep baseline" wording for mixed stop+scope requests, delayed authorization tightening/revocation, and a "no confirmation needed" exemption that weakened AI-restatement → human-confirmation. These were fixed; the four labels are now clarification / operational instruction / functional·scope·acceptance change / rule·authorization-boundary change, with a mixed-or-ambiguous higher-category fallback.
- PASS: dry-run creates no files; applied initializer creates the template set and 3 adapters in a temporary directory; placeholders resolved.
- PASS: package and generated-project relative Markdown links resolve; skill frontmatter valid; whitespace check clean.
- Renamed: the package now says "project basic law" instead of "project constitution" across README (zh/en), method-basis, context-and-harness, template AGENT.md, and this log. Terminology only; no behavioral change.

## 2026-10-30 basic-law amendment mechanism

- Confirmed: originator chose the full option (documentation plus a checker script) and the standard amendment threshold (amendment + explicit per-clause human confirmation + proposal/decision separation + version and records + post-change re-verification).
- PASS: initializer dry-run creates no files; applied run creates 9 templates and 3 adapters (12 files) in a temporary directory; placeholders resolved; generated project contains the [BL-xxx] clauses and the amendment log.
- PASS: package and generated relative Markdown links resolve (53 across 32 files); frontmatter valid; whitespace clean; no legacy wording remains in SKILL, references, templates, or README pages.
- PASS: check_basic_law.py end-to-end in a temporary project — first freeze (version 1) then check PASS; tampering BL-004 → VIOLATION, exit 1; re-freeze without --force → exit 2; --force with unrecorded amendment → exit 2; recording the amendment then re-freeze → version 2, check PASS; new BL-007 → VIOLATION; removed heading → VIOLATION; duplicate ID → VIOLATION; restored file → PASS.
- Reviewed: basic-law-change.md defines L1/L2/L3, the standard procedure, discussion/proposal/decision states, anti-bypass checks and limits; template AGENT.md carries stable [BL-xxx] IDs and a 受保护条款 statement; change-control, intent-confirmation, SKILL and both READMEs point to the same procedure; the intent and STATUS templates gained a minimal mid-run supplement record field.
- Not verified: real model behavior in these scenarios; Git/CI protection, PR review and hook enforcement are host-side and not configured here. The checker only helps when actually run; Markdown is not an enforcement mechanism.

未进行真实模型对“运行中临时补充、补充后改道、紧急打断”等场景的行为评测；文档指导不能保证宿主执行，也未新增运行时强制机制。检查脚本需由人或CI实际运行才生效。

## 2026-10-30 safety baseline and host wiring

- Confirmed: originator chose the full option (safety red lines + reference doc + host-neutral hook/CI examples) and noted that developers may not use GitHub; the wiring is therefore platform-neutral, with local git hooks as the primary path and any CI or job runner executing the same entry script.
- PASS: template AGENT.md adds [BL-101]–[BL-106] safety red lines and points [BL-004] at them; generated projects contain 12 protected clauses; the initializer creates 10 files with the default adapter (12 with three adapters).
- PASS: ci-check.sh in a temporary project — before the baseline: WARN + PASS (exit 0); after freeze: PASS; tampered BL-004: FAIL (exit 1); unresolved placeholder: FAIL (exit 1); fake AWS key pattern: FAIL (exit 1). The script resolves its own project root, so it also works when invoked from outside the project.
- PASS: pre-commit.sh — a normal commit passes; a commit that changes a protected clause is blocked (nonzero exit); `git commit --no-verify` succeeds (bypass documented, not a gate); a missing scripts/ci-check.sh skips with a warning (exit 0).
- PASS: package and generated relative Markdown links resolve (48 links / 22 files and 14 / 12 files; 62 / 34 combined); frontmatter valid; whitespace clean.
- Reviewed: safety-baseline.md and host-wiring.md describe platform-neutral wiring (local hook, one entry script, a platform matrix for GitHub/Gitee/GitLab/Gitea/Jenkins/self-hosted) and state the limits. Platform-specific CI behavior, server-side branch protection, Windows shells and real model behavior were not run or verified here.

## 2026-10-30 README workflow and expectations

- Added: a workflow diagram (Mermaid, with a plain-text fallback inside `<details>`) for intent confirmation → Spec → Plan → Build → Test → Deploy → Maintain, plus three tables redrawn for this project: six stages × artifacts × human decisions × evidence; token and cost basis; expected maintenance cost profile.
- Reviewed: the tables are redrawn in this project's terms rather than copied from the supplied course deck; the deck is cited only as framing, and its experience numbers are labelled illustrative, not measured or promised.
- PASS: package Markdown links resolve; code fences and tables are balanced; whitespace clean. Mermaid rendering was not verified on any specific host.

## 2026-10-30 background reading added (de-emphasized)

- Added: `background/whitepapers-zh/` with seven unofficial Chinese translations of publicly released AI-agent whitepapers plus their figures, an index, and a copyright/usage notice. Both READMEs now present the skill as the main deliverable and treat this folder as optional background.
- Excluded on purpose: the unrelated consumer-oriented Google manual (mistakenly included), the manufacturing course decks (training material, not whitepaper translations), the zip archive, build scripts, extracted-text intermediates and `.DS_Store`.
- PASS: personal-information scan of the included HTML files found no emails, phone numbers, ID numbers, local user paths or key patterns; "护照" in one document refers to the "Digital Passport" concept, not personal data. Images were not OCR-scanned.
- PASS: all 28 image references inside the included HTML files resolve; package Markdown links resolve (54 links / 23 files); whitespace clean.
- Not verified: whether each translation is authorized for redistribution by the original rights holders. The translations are included as unofficial study references, are not covered by the MIT license, and will be removed if a rights holder requests it.
- Size: `background/whitepapers-zh/` is about 9.9 MB.

## 2026-10-30 V2 Batch A — implemented and exercised in GitHub Actions

Approved scope: PF-02, PF-03, PF-04, PF-05 only. Isolated branch `feat/v2-batch-a-contracts`; unmerged draft PR [#1](https://github.com/8778fkv694-hub/pre-flight/pull/1).

### Change inventory

- PF-02: New schema 2 hashes protected clauses and indented continuation paragraphs, including those after blank lines. Existing schema 1 baselines retain the original single-line hash behavior; upgrading to schema 2 requires explicit migration.
- PF-03: Re-freezing schema 2 requires an accepted structured amendment record with complete old/new hash-diff matching; this **does not** authenticate an actual human or replace protected-branch review.
- PF-04: New read-only `check_project_contract.py` checks current artifact metadata, references, optional structured receipts and STATUS markers. `--mode audit` is non-blocking, `--mode check` rejects deterministic errors. Historical pinned versions are warnings without available version history, not automatically invalid.
- PF-05: Spec/Plan/Verification templates record minimum WP, Spec revision/clause, Case, implementation identity, execution environment and evidence associations.
- GitHub Actions workflow `.github/workflows/batch-a-validation.yml` runs checks on the branch/PR.

### Verification evidence

- **PASS:** [GitHub Actions workflow run 40997741500](https://github.com/8778fkv694-hub/pre-flight/actions/runs/40997741500), commit `4912ce6e7ded62b7ae5ac3d5379e4a7e336598ac`, Python 3.11, Ubuntu runner.
- **PASS:** 10 unittest cases including duplicate IDs, legacy hash compatibility, multiline continuation hashing (also across blank lines), rejected unauthorized diff, version-pinning and future-version handling, draft contract validation.
- **PASS:** Actual CLI lifecycle in disposable temp projects: first freeze, check, detect tampering, reject an unapproved re-freeze, accept a matching structured amendment, re-freeze and check; separate legacy schema 1 → schema 2 migration and post-migration tamper detection.
- **PASS:** Python syntax compilation of scripts/tests.
- **PASS:** `init_project.py --apply` creates 10 draft files in a temporary project; `check_project_contract.py --mode check` reports **0 errors, 0 warnings** for that generated draft.
- Earlier CI failures surfaced regex and fixture defects; those failures were corrected before the successful run. Successful run is the authoritative evidence, not earlier attempts.

### Remaining limitations before production adoption

- Only Python 3.11 on a Linux GitHub runner was exercised, not Windows/macOS or real coding-agent compliance.
- A matching hash diff and metadata record do not authenticate a human approver; PR review and permissions remain external requirements.
- The contract checker validates explicitly parseable single-current-artifact references; it does **not** prove semantic correctness, completeness of impact analysis, or past-version acceptance when version history is missing.
- Existing projects are not migrated automatically. The new schema-2 amendment contract may require manual setup when upgrading project-local checker copies.
- README artwork/other V2 batches are not part of this PR.

## 2026-10-30 anti-self-amendment guard and cross-seam perception check

- Confirmed: originator confirmed the candidate Intent restatement covering both anti-self-amendment detection in `ci-check.sh` and the cross-seam user-perceived closed-loop criterion (`写→通→刷→见`) in `workflow.md` before file changes.
- PASS: `ci-check.sh` end-to-end in a temporary Git repository — clean tree passes without `AMENDMENT_TOUCHED`; modifying `AGENT.md` + `basic-law-log.md` + re-freezing `basic-law.lock.json` triggers `WARN: AMENDMENT_TOUCHED` locally (exit 0); setting `CI_REQUIRE_AMEND_ACK=1` without `CI_AMEND_APPROVED=1` blocks unapproved self-amendment (`FAIL: AMENDMENT_TOUCHED`, exit 1); setting `CI_REQUIRE_AMEND_ACK=1 CI_AMEND_APPROVED=1` passes (exit 0); committed self-amendment compared via `CI_BASE_REF=HEAD~1 CI_REQUIRE_AMEND_ACK=1` also fails as expected (exit 1).
- PASS: package Markdown relative links resolve (54 links across 23 files); initializer dry-run and `--apply` pass in a temporary directory.
- Not verified: server-side CI secret/variable protection (`CI_AMEND_APPROVED` must be restricted to human approvers on the CI host to prevent pipeline scripts from self-setting it).
