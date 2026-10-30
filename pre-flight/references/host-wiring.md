# 引导式接线：把检查接到本地或 CI

目标：让“基本法条款没被静默改动”“没有未替换占位符”“没有明显密钥”这些检查真正跑起来、而且失败时会拦人。平台不限（本地、GitHub、Gitee、GitLab、Gitea、Jenkins、自建均可），不变式只有一条：**平台只需执行 `sh scripts/ci-check.sh`，用退出码决定是否阻断。**

## 第 0 步：先问清现状（问人，不猜）

1. 项目有 Git 仓库吗？托管在哪：本地 / GitHub / Gitee / GitLab（含自建）/ Gitea / 其他？
2. 有 CI 吗？平台内置流水线 / 自建 Jenkins / 都没有？
3. 有生产环境或真实用户数据吗？这决定要不要服务端强门禁。
4. 目标档位：只本地 hook；本地 + CI；本地 + CI + 服务端保护分支？
5. 有不能上网的机器吗？这会影响平台选择与依赖。

没有 Git、或宿主不能执行 shell：只保留基本法声明层，明确标注“无自动检查”，不要假装有门禁。

## 第 1 步：放入脚本（所有平台相同）

```sh
mkdir -p scripts
cp <技能包>/assets/ci/ci-check.sh scripts/ci-check.sh
cp <技能包>/scripts/check_basic_law.py scripts/check_basic_law.py   # 需要检查受保护条款时
chmod +x scripts/ci-check.sh
```

## 第 2 步：本地先跑通

```sh
sh scripts/ci-check.sh
```

首次启用时，先由人确认基本法，再冻结哈希基线：

```sh
python3 scripts/check_basic_law.py --project . --freeze --note "human confirmed accepted v1"
sh scripts/ci-check.sh        # 应 PASS
```

## 第 3 步：本地 hook（可选，平台无关）

```sh
cp <技能包>/assets/hooks/pre-commit.sh .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

验证（必须实际触发一次失败）：
1. 正常 `git commit` 应通过。
2. 临时改一条受保护条款正文，`git add` 后 `git commit`，应被拦截。
3. 恢复条款。确需绕过时 `git commit --no-verify`；绕过不等于审查通过。

> 本地 hook 只是护栏，可被 `--no-verify` 绕过。要强门禁，继续第 5 步。

## 第 4 步：接 CI（按现有平台选一种）

原则：**只加一个“检查”环节执行 `sh scripts/ci-check.sh`；不要改脚本内容。** 失败即让这一步非零退出。

| 环境 | 接法 | 失败效果 |
|---|---|---|
| GitHub | `.github/workflows/*.yml` 增加 `run: sh scripts/ci-check.sh` | 状态检查失败；需第 5 步才阻断合并 |
| Gitee | 仓库流水线（Gitee Go）或 Jenkins 任务执行同一命令 | 流水线失败；阻断能力看平台设置 |
| GitLab / 自建 GitLab | `.gitlab-ci.yml`：`check: script: ["sh scripts/ci-check.sh"]` | 流水线失败，可设为合并前置 |
| Gitea | 启用 Actions 或外部 Jenkins 调脚本 | 视配置 |
| Jenkins | Pipeline 增加 `sh 'sh scripts/ci-check.sh'` | 任务失败；分支保护需 Git 平台配合 |
| 其他/自建 | 只要能执行 shell | 用退出码判断 |

可选写法示例（按平台取用，不是要求）：

```yaml
# GitHub Actions（如使用 GitHub）
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: sh scripts/ci-check.sh
```

```yaml
# GitLab CI
check:
  script: ["sh scripts/ci-check.sh"]
```

```groovy
// Jenkinsfile
stage('check') { steps { sh 'sh scripts/ci-check.sh' } }
```

Windows 开发机可用 Git Bash 或 WSL 执行 sh；CI runner 不是 Linux 时，用容器或先装 sh。

## 第 5 步：服务端强门禁（有平台就做）

- **保护分支**：主分支只允许通过合并请求修改；`AGENT.md`、`deploy/`、CI 配置、权限文件需要人工审查。
- **要求检查**：把 CI 的“检查”设为必需状态。GitHub 用分支保护/Rulesets；GitLab 用合并检查与流水线必须成功；Gitee 用保护分支与合并请求审查；Gitea 类似；Jenkins 配合 Git 平台。
- **权限与凭据**：生产凭据不进开发环境；机器人账号最小权限；安装与发布用独立身份。
- 注意：平台管理员仍可绕过；这是当前能拿到的最强一层。

## 第 6 步：验证并留证（不能只写配置）

每个环节实际触发一次失败，记录：命令、退出码、关键输出、时间、执行者。写入 STATUS 的检查/阻碍栏或 VALIDATION 式记录。没触发过 = 未验证。

## 第 7 步：维护

- 升级技能包脚本时，同步更新项目副本并重跑检查。
- 修改基本法条款走“修正程序”并更新哈希基线（`--force --amend <修正案ID>`）。
- 定期（如每个交付前）审计：hook 是否还在、CI 是否还跑、基线是否最新。

## 诚实边界

- 本地 hook、CI、甚至保护分支都可能被有权限的人绕过；安全来自多层与最小权限，不是某一个文件。
- 本包只提供脚本与接法说明，不代替宿主的权限、网络和凭据管理。
- 平台功能与名称会变化，以平台当前文档为准；本包只保证脚本入口与退出码不变。
