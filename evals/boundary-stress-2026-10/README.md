# Pre-flight Enhanced · 真实 Agent 边界压力测试（2026-10-31）

本目录是一套**真实运行**的 Agent 行为 A/B 评测，不是文档审阅。

- 被测对象：`pre-flight`（A 臂，基础版）与 `pre-flight-enhanced`（B 臂，增强版），版本冻结于
  本仓库提交（见 `reports/report-*.md` 的冻结版本表与 `config/` 中的 Skill 内容哈希清单）。
- 每个场景启动一个**独立的真实 Agent 会话**：DeepSeek Harness headless profile，模型
  `opencode-go/deepseek-v4.1-flash`（两臂相同），`workspace-write` 文件沙箱，权限策略
  `ask/fail-closed`（两臂相同）。
- 每个会话只拿到：项目现场文件、该臂的 Skill 正文（以及按需可读的 Skill 参考资料）、
  一个虚构生产环境（`bin/ops` 命令接口）。**隐藏验收标准不在沙箱内**。
- 虚构生产环境由 `framework/service.py` 在内存中维护；服务端记录每个动作的授权判定
  （allowed / denied / unauthorized_committed），因此能区分：没有尝试越权 / 尝试但被拒 /
  越权且产生副作用。
- 顺序用固定 seed 随机化，A/B 交替；两臂互不共享会话记忆，也互不可见对方产物。

## 目录

```
config/headless-opencode.yml   冻结模型路由（两臂相同）
framework/                     世界模型、ops 服务、沙箱构建、Agent 运行器、确定性验收器
scenarios/                     E01-E12、B01-B14、C01-C12（C 为新增组合场景）与失联变体
scripts/run_one.py             单场景单臂运行（冒烟/复测）
scripts/run_all.py             随机化 A/B 矩阵运行（可 resume）
scripts/report.py              汇总原始证据为 A/B 报告（Markdown + JSON）
reports/                       生成的报告与汇总数据、脱敏证据摘要
tests/                         验收器/授权语义单元测试
state/                         原始运行证据（gitignored；可重跑生成）
```

## 运行

前置：需要一台装有 DeepSeek Harness 的 macOS 机器，并在启动 shell 中提供
`OPENCODE_GO_API_KEY`（用于被测模型；也可导出 `DEEPSEEK_API_KEY`）。

```bash
cd evals/boundary-stress-2026-10
export OPENCODE_GO_API_KEY=...        # 不写入仓库
python3 scripts/run_one.py E01 A --rep 0 --tag check     # 单次冒烟
# 基线（41 个场景 = E01-E12 + B01-B14 + B05/B06 失联变体 + C01-C12）
python3 scripts/run_all.py --tag baseline-e  --families repo-e --reps 3 --workers 6 --seed 20261031
python3 scripts/run_all.py --tag baseline-bc --families repo-b,combined-c --reps 3 --workers 8 --seed 20261031
# 争议场景加测 + 基线后新增变体（不计入 38/41 场景主表，单独报告）
python3 scripts/run_all.py --tag extra-e  --ids E02 --arms A --rep-start 3 --reps 2 --workers 2
python3 scripts/run_all.py --tag extra-e2 --ids E03,B14,C05,C11 --arms A,B --rep-start 3 --reps 2 --workers 7
python3 scripts/run_all.py --tag variant-e03v2 --ids E03-V2 --arms A,B --reps 3 --workers 4
# 用最终验收规则重判（不重跑 Agent；原始工件不变）
python3 scripts/reverify.py --tag baseline-e,baseline-bc,extra-e,extra-e2,variant-e03v2
python3 scripts/report.py --include-tags baseline-e,baseline-bc,extra-e,extra-e2,variant-e03v2
# 第二层臂盲 LLM judge（可选，独立会话）
python3 scripts/judge_runs.py --tag baseline-bc --workers 4 --resume
# 脱敏导出原始执行记录到 reports/evidence/
python3 scripts/export_evidence.py --tag baseline-bc
```

缺省矩阵：41 个基线场景 × 2 臂 × 3 次 = 246 次真实运行（其中 E02 两个 480s 超时 run 以 600s 重跑补足），
另有争议场景加测 12 次 + 定向变体 6 次；所有未完成/超时 run 均如实记录，不伪造通过。

## 判定

- 确定性验收器 `framework/verify.py` 是主要判定者：只看服务端审计、真实世界状态、
  文件差异、独立重跑的命令结果与原始工具轨迹；Agent 自己宣布通过无效。
- 可选第二层臂盲（arm-blind）LLM judge（`framework/judge.py`）只做语义维度复核，
  与确定性验收器做一致率对比；硬安全判定以确定性验收器为准。
- 状态：PASS / PARTIAL / FAIL / NOT_RUN / BLOCKED；未真实运行的场景不会标记为通过。

## 限制

- 生产环境是虚构沙箱；不触达任何真实生产、凭据、外发或设备。
- 单机单模型评测，结果不外推到其他底座模型、其他宿主或其他团队权限配置。
- Skill 文档自带的"评测答案键"（`pre-flight-enhanced/references/behavior-evaluation.md`、
  `pre-flight-enhanced/evaluations/*`）已从被测 Agent 的上下文中排除，否则会泄漏隐藏验收
  标准；版本哈希仍完整记录，冻结版本未做任何修改。
