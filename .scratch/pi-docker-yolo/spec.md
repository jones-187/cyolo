## Problem Statement

用户主要使用宿主 Pi，希望在 Docker 中无人值守工作。现有 cyolo 为 Claude/Codex 提供两套旧容器，只映射启动项目；跨项目搜索、修改和不同 cwd 的并发会话受限。完整入口逻辑放在宿主 shell 配置中，无法随项目版本维护。Pi 的配置、扩展和 MCP 依赖宿主文件、环境变量及运行时，迁移不能破坏这些现有能力。

## Solution

建立一个独立、长期运行的 Pi YOLO 容器。固定映射项目工作区、临时目录和 cyolo 项目；从已映射根目录的任意深度子目录启动时保持 cwd。宿主与容器共享 Pi 配置和会话。程序在容器独立安装，正常启动要求与宿主 Pi 版本一致，显式应急参数可以跳过版本差异。仓库作为入口和 Docker 配置的事实源；旧 Claude/Codex 入口保留并标记停止维护。

## User Stories

1. As a Pi 用户, I want 裸 cyolo 和 cyolo pi 都启动 Pi, so that 日常入口简单一致。
2. As a Pi 用户, I want 项目工作区整体读写映射, so that 一个任务可以读取和修改多个项目。
3. As a Pi 用户, I want 从任意深度子目录启动并保持 cwd, so that 不用返回项目根目录。
4. As a Pi 用户, I want 从已映射的临时目录和 cyolo 项目目录启动, so that 可以处理临时材料和维护本项目。
5. As a Pi 用户, I want 未映射 cwd 立即报错, so that 不会意外改变挂载或打断其他会话。
6. As a Pi 用户, I want 多个终端共享长期 Pi 容器, so that 不同项目的会话能同时运行。
7. As a Pi 用户, I want 退出一个 Pi 不停止容器, so that 其他 Pi 会话继续工作。
8. As a Pi 用户, I want 宿主和容器共享全部 Pi 配置及会话, so that 模型、扩展和历史不重复维护。
9. As a Pi 用户, I want Pi 与 Codex 配置目录读写共享, so that 配置更新和 MySQL 审计可以正常保存。
10. As a Pi 用户, I want 保留 SSH/Git/Java/Maven/代理/网络能力, so that 已有开发工作不受影响。
11. As a Pi 用户, I want 自动传递导出的环境变量并排除宿主运行变量, so that 新增 MCP 变量不需要维护白名单。
12. As a Pi 用户, I want secrets 不写进仓库、不打印到日志, so that 可以安全发布源码。
13. As a Pi 用户, I want 容器独立安装 Node 24 和准确 Pi 版本, so that 不依赖整个宿主 NVM。
14. As a Pi 用户, I want 启动前比较两边 Pi 版本, so that 共享配置使用一致的程序版本。
15. As a Pi 用户, I want 版本错误给出更新和应急命令, so that 网络故障时知道如何继续。
16. As a Pi 用户, I want 显式允许版本不一致, so that 必要时能使用已有旧版本。
17. As a Pi 用户, I want 缺镜像时给出构建命令, so that 普通启动不隐含联网安装。
18. As a Pi 用户, I want 容器内有 Pi 进程时拒绝重建, so that 不中断任务。
19. As a Pi 用户, I want 容器内保留免密码 sudo, so that Agent 可在容器内安装必要工具。
20. As a Pi 用户, I want 当前五个 MCP 原样保留, so that 不新增服务或改变既有业务规则。
21. As a Pi 用户, I want MCP 依赖在构建时就绪且 Grafana 缓存持久化, so that 第一次调用不临时下载。
22. As a Pi 用户, I want 禅道 MCP 使用通用 node 且安装脚本一致, so that 宿主与容器分别使用自己的 Node。
23. As a Pi 用户, I want 生产 MySQL 查询保留人工文字确认, so that 该操作继续作为无人值守例外。
24. As a Pi 用户, I want Pi 参数完整透传并支持明确分隔符, so that 可以继续使用模型、恢复会话和 print 等参数。
25. As a Pi 用户, I want 旧 Claude/Codex 入口警告后仍可使用, so that 应急任务不丢失旧能力。
26. As a 项目维护者, I want shell 只调用仓库脚本, so that 实现与文档可追踪维护。
27. As a 项目维护者, I want 项目级 GitHub 身份和 SSH 配置, so that 不影响其他仓库账户。
28. As a 项目维护者, I want 本地 spec 与独立 tickets, so that 子代理可按依赖实施并逐项验收。

## Implementation Decisions

- 新建 cyolo 项目，Git 默认分支 main。项目提交身份为 GitHub 用户名及用户指定邮箱，SSH 使用已验证的密钥；不修改全局账户。
- Shell 包装函数仅调用项目入口。裸入口默认 Pi；cc/claude、cx/codex 调用原有独立实现并警告，不扩展旧镜像。
- Pi 独立 Compose 项目和长期容器，容器名 pi_yolo_env。保持宿主用户名、UID、GID和 cwd；固定工作区、临时目录及 cyolo 项目映射。
- Pi 和 Codex 用户配置整体读写共享；Agent skills、OpenCode 配置和禅道部署目录按运行需要映射。SSH/Git配置只读，Maven/Java只读，Maven缓存读写。
- 使用 Node 24 bookworm 镜像，构建时读取宿主 Pi 准确版本并独立安装。正常启动不联网安装；版本不匹配立即失败，明确应急参数仅跳过版本差异。
- 更新命令检查容器 Pi 进程；运行中拒绝更新。检查失败不能假装无进程而继续替换容器。
- Pi包装参数为 --build、--allow-version-mismatch；--之后全部交给Pi，其余参数保持顺序和字面值。
- 仅支持终端 docker exec。保留退出码和免密码sudo。
- 环境变量从当前宿主导出环境按黑名单传给本次执行，不打印值、不写进镜像或仓库。不将宿主身份、PATH、Node/Java/Maven路径、IPC会话路径带进容器。
- 当前审批扩展已卸载，不恢复。MCP及生产人工确认保持现状，仅禅道Node命令及安装器同步改成通用node。
- Python依赖和uv/uvx、Grafana MCP在构建时就绪；Grafana使用独立Docker named volume保存uv缓存，启动不依赖临时联网下载。
- 本地 tracker 使用 ready-for-agent/in-progress/done/blocked。首次提交收录规范、spec和tickets，作为评审基准。

## Testing Decisions

- 已确认测试入口为 cyolo 命令。使用 Docker/宿主Pi的系统边界替身观察退出码、错误提示、cwd、参数和容器收到的环境；不绑定内部函数实现。
- 一次一个行为测试，先失败再实现；覆盖子目录、未映射cwd、环境黑名单、参数、缺镜像、版本和运行中更新保护。
- 禅道安装器通过实际注册命令边界验证node可移植性，不调用生产MCP。
- 仓库暂无测试先例。使用标准库测试工具和shell语法检查，不引入大型测试框架。
- 最终执行全部行为测试、Compose配置检查、构建与真实Pi启动及五个MCP加载检查。生产SQL、创建禅道Bug及其他业务写操作不在验证范围。
- 评审分为仓库规范和需求两轴；提交前检查敏感数据和未提交内容。

## Out of Scope

- 无终端适配、自动审批或生产查询自动放行。
- 新增MCP、导入Claude MCP、恢复已卸载扩展。
- 改造旧Claude/Codex镜像、删除旧容器或目录。
- 自动创建GitHub仓库、添加未提供的remote、推送。
- 映射整个宿主HOME/NVM、Docker socket、宿主keyring。
- 处理同一项目同时编辑产生的业务冲突；新增锁、重试或同步层。
- 删除历史会话和配置备份，修改其他无关skills或宿主账户。

## Further Notes

宿主与容器共享读写配置，任一方修改会立即影响另一方。并发修改同一会话或配置不具备隔离保证。版本应急启动接受旧Pi读取新版配置的兼容风险。生产查询可能等待用户文字确认，这是明确保留的例外。技能仓库存在用户已有未提交内容，本次只处理禅道安装器。远程由用户手动创建后提供。
