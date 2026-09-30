# 02: 禅道 MCP 在宿主和容器使用各自 Node

**What to build:** 现有禅道MCP注册及安装脚本都使用通用node；再次安装不会恢复宿主NVM绝对路径。

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] 当前MCP的Node命令改为node，保留其他MCP配置与业务规则。
- [ ] 安装器生成node并能识别迁移旧绝对路径。
- [ ] 注册命令边界验证通过，不运行生产SQL或修改业务数据。
- [ ] 用户已有skills改动保留，提交只包含本次必要修改。
