# {{PROJECT_NAME}} — 项目共同指导

本文件为规则正文，所有客户端入口引用它。不要在入口复制不同规则。

- 当前状态：[STATUS.md](STATUS.md)
- 人的意图：[intent.md](docs/sdlc/plan/intent.md)
- 做好标准：[spec.md](docs/sdlc/design/spec.md)
- 实施计划：[plan.md](docs/sdlc/build/plan.md)
- 验证：[verification.md](docs/sdlc/test/verification.md)
- 交付：[delivery.md](docs/sdlc/deploy/delivery.md)
- 维护：[maintenance.md](docs/sdlc/maintain/maintenance.md)

## 项目与架构

项目目的、用户、技术栈及源码入口：待核实；从人的意图推导，不能把模板当技术选型。

## 实际命令

安装、开发、类型/静态检查、定向测试、完整回归、构建命令均待建立并实际运行后回填；缺项不是通过。不要执行猜测的命令。

## 协作规则

先核对工作目录、分支、未提交改动及当前工作包；保留他人工作。人的当前明确要求优先于历史偏好，歧义与决定留痕。范围内自主实施，关键新决定才询问。并行工作明确写集合和共享资源；worktree不隔离设备或数据。

Spec冻结、实现验收、正式生效分别记录；新版本未验不得替代稳定基线。失败/跳过/未验如实披露。写后验证实际结果，效果未知先只读对账，不盲目重放。发布和生产操作核对适用授权。

项目特有规范、真实自动检查及权限边界：待团队明确。Markdown是指导，不能当已强制执行的安全机制。
