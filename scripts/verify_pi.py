#!/usr/bin/env python3
"""启动 Pi 并读取状态；不发送 prompt，不调用模型或业务工具。"""

import json
import queue
import subprocess
import threading


def main():
    messages = queue.Queue()
    process = subprocess.Popen(
        ["pi", "--mode", "rpc", "--no-session"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )

    def receive():
        for line in process.stdout:
            try:
                messages.put(json.loads(line))
            except ValueError:
                continue
        messages.put(None)

    threading.Thread(target=receive, daemon=True).start()
    try:
        process.stdin.write('{"id":"verify-state","type":"get_state"}\n')
        process.stdin.flush()
        while True:
            message = messages.get(timeout=45)
            if message is None:
                raise RuntimeError("Pi 提前退出")
            if message.get("id") == "verify-state":
                if not message.get("success"):
                    raise RuntimeError("Pi 无法返回状态")
                if message.get("data", {}).get("isStreaming"):
                    raise RuntimeError("Pi 意外进入模型请求")
                print("Pi 初始化成功并返回状态；未发送模型请求，未调用业务工具")
                return 0
    except Exception as error:
        print(f"Pi 验证失败（{type(error).__name__}），未输出配置或凭据")
        return 1
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


if __name__ == "__main__":
    raise SystemExit(main())
