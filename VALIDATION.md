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
