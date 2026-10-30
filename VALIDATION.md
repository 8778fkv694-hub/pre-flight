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

- PASS: repeated initializer checks after template changes, including draft constitution, absent confirmation record, and unconfirmed Spec state. These inspect document output, not agent behavior.
- PASS: separate Chinese/English README pages, reciprocal language links, package and generated local links.
- PASS: skill frontmatter validator and whitespace check.
- Reviewed: both provided references mapped to workflow/templates; the explicit AI-restatement → human-confirmation requirement is reflected in skill, lifecycle, versioning, template and both README pages.

未进行真实模型对“模糊输入/修改后重确认/已有确认接续”等场景的行为评测；文档指导不能保证宿主执行。未新增或宣称存在CI、运行时强制门禁或自动发布能力。

## 2026-10-30 mid-run supplement rule

- Confirmed: originator confirmed the AI restatement of the mid-run supplement rule (four-type triage) and chose formal inclusion in the skill before any file change. Confirmation came from the originator's reply in session, not from an agent or generated file.
- PASS: dry-run creates no files; applied initializer creates 8 templates and 3 adapters in a temporary directory; placeholders resolved.
- PASS: package and generated-project relative Markdown links resolve (31 and 13 links); skill frontmatter valid; whitespace check clean.
- Reviewed: the four types (clarification, in-scope operation, functional/scope change, rule/constitution change) are expressed consistently in SKILL.md, intent-confirmation.md, change-control.md, template AGENT.md, and both README viewpoints. The rule preserves the existing AI-restatement → human-confirmation requirement, keeps intent confirmation separate from operation authorization, and does not add runtime enforcement.

未进行真实模型对“运行中临时补充、补充后改道、紧急打断”等场景的行为评测；文档指导不能保证宿主执行，也未新增运行时强制机制。
