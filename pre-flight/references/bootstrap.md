# 初始化与客户端适配

初始化前核对目录和用户要求。脚本仅用于全新空目录，默认dry-run；已有项目手工对照模板做最小增量，不能覆盖原入口或资料。

```sh
python3 scripts/init_project.py --target /absolute/path/new-project --project-name "项目名"
python3 scripts/init_project.py --target /absolute/path/new-project --project-name "项目名" --apply
```

默认生成AGENTS.md薄入口；需要其他入口时加 `--adapters agents,claude,gemini`。不需要任何入口时用 `--adapters none`。脚本不初始化Git、不安装依赖、不启动服务、不配置CI、不部署。

## 规则正文与读取

AGENT.md是本方案选定的统一项目正文，不是所有客户端自动发现的标准文件名。AGENTS.md/CLAUDE.md/GEMINI.md只含指向AGENT.md、STATUS.md的相对链接与读取要求。自动发现行为取决于客户端版本、工作目录、项目设置和实际产品支持；本包不声称已在所有客户端实测。

首次使用，要求执行Agent复述AGENT.md中的项目名、状态入口和真实检查命令，核对其确实读取；只验证文件存在不足以证明加载。若客户端不支持入口或Skill包，直接将SKILL.md及目标AGENT.md路径提供给它，要求先读取。薄入口不可依赖未经验证的专有导入语法。

支持Skill目录的宿主可安装整个pre-flight目录到其受支持技能根。原样移动整个目录保留references/assets/scripts相对路径。agents/openai.yaml仅为可选宿主UI元数据，其他宿主可以忽略；不要把它当跨产品协议。

## 新项目建立后

先填Intent并核实关键目标，再按需完善Spec、Plan。模板命令是“待核实”，不是可执行脚手架；选定技术栈后真正创建源码、运行命令并回填。用户只要规划时停止在相应交付点。
