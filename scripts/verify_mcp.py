#!/usr/bin/env python3
"""只初始化现有 MCP 并列出工具，不执行任何业务工具。"""

import json
import os
from pathlib import Path
import queue
import subprocess
import threading
import time
import tomllib


SERVERS = (
    "public-cloud-log-diagnostics",
    "mysql-query-diagnostics",
    "zentao-bug-ops",
    "grafana-test",
    "grafana-prod",
)


def receive_lines(stream, messages):
    for line in stream:
        try:
            messages.put(json.loads(line))
        except (ValueError, TypeError):
            continue
    messages.put(None)


def response(messages, request_id, timeout=45):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        item = messages.get(timeout=max(0.01, deadline - time.monotonic()))
        if item is None:
            raise RuntimeError("MCP 进程提前退出")
        if item.get("id") == request_id:
            if "error" in item:
                raise RuntimeError("MCP 返回协议错误")
            return item["result"]
    raise TimeoutError("MCP 未及时响应")


def check_server(name, config):
    environment = os.environ.copy()
    environment.update(config.get("env", {}))
    command = [config["command"], *config.get("args", [])]
    messages = queue.Queue()
    process = subprocess.Popen(
        command,
        cwd=config.get("cwd"),
        env=environment,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    threading.Thread(
        target=receive_lines, args=(process.stdout, messages), daemon=True
    ).start()

    def send(message):
        process.stdin.write(json.dumps(message) + "\n")
        process.stdin.flush()

    try:
        send({
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05", "capabilities": {},
                "clientInfo": {"name": "cyolo-verification", "version": "1"},
            },
        })
        response(messages, 1)
        send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        send({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        tools = response(messages, 2).get("tools", [])
        if not tools:
            raise RuntimeError("MCP 未提供工具")
        print(f"{name}: 初始化成功，{len(tools)} 个工具；未调用业务工具")
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def main():
    with (Path.home() / ".codex/config.toml").open("rb") as config_file:
        configurations = tomllib.load(config_file).get("mcp_servers", {})
    failures = 0
    for name in SERVERS:
        try:
            check_server(name, configurations[name])
        except Exception as error:
            # 错误对象可能带有凭据或服务返回内容，只打印类型。
            print(f"{name}: 验证失败（{type(error).__name__}），未输出服务日志或配置值")
            failures += 1
    return int(failures > 0)


if __name__ == "__main__":
    raise SystemExit(main())
