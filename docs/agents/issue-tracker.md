# 本地任务跟踪

- Tracker：本地 Markdown 文件，不发布到外部服务。
- 需求：`.scratch/pi-docker-yolo/spec.md`。
- Tickets：`.scratch/pi-docker-yolo/issues/`，每个任务独立文件，依赖写在 Blocked by。
- 状态词：`ready-for-agent`、`in-progress`、`done`、`blocked`。
- 外部 GitHub 仓库由用户手动创建。提供 SSH remote 后再添加 origin；不自动创建或推送。
- 本次评审基准：实施前的需求与任务提交。评审包含本项目实现以及禅道安装脚本的必要改动。
