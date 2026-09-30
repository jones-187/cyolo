# 01: 建立仓库并从固定工作区启动 Pi

**What to build:** 裸 cyolo 和 cyolo pi 从固定映射目录及任意深度子目录启动长期共享 Pi 容器，保持 cwd，使用共享配置，安全传递参数和宿主导出环境。

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] 项目Git身份独立，main分支，敏感数据规范和忽略规则齐全。
- [ ] 固定映射工作区、临时目录和项目目录；任意深度子目录可启动，未映射目录直接失败。
- [ ] Pi配置与会话、Codex配置整体读写共享，现有SSH/Git/Java/Maven能力保留。
- [ ] 独立Pi容器共享多会话，退出单会话不停止容器。
- [ ] 导出环境按黑名单传递，不打印敏感值，Pi参数原样透传。
- [ ] 命令入口行为测试先失败再通过。
