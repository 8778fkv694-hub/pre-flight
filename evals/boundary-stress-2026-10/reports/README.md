# 评测报告索引

- `ANALYSIS-2026-10-31.md`：正式分析报告（结论、A/B、三类错误、根因分类、复现方法、限制、下一轮建议）。
- `report-all.md`：由 `scripts/report.py` 从原始 verdict 自动生成的完整表格（逐场景、成本、judge 一致率、安全硬失败清单、失败发现）。
- `summary-all.json`：上述报告的机器可读汇总。
- `acceptance-corrections.md`：测试期间对验收器/场景验收规则的修正记录（每条都有触发 run 与 before/after；安全判定未放宽）。
- `scenario-static-audit.md`：对 42 个场景的独立静态审计（泄漏、过严、可达性、一致性、残余风险）。
- `evidence/<tag>/`：逐 run 脱敏原始执行记录（压缩 JSON：prompt 任务段、完整 tool trace、服务端 audit、world 快照、最终答复、verdict、模型/权限配置、skill 哈希）。`index.json` 为运行索引。

运行相关命令见仓库根 `README.md`。所有原始（未脱敏）证据在 `state/runs/`（gitignored，可由 `scripts/run_all.py` 重跑生成）。
