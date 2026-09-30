#!/usr/bin/env python3
"""只报告是否有 Pi 进程，不输出进程参数。"""

from pathlib import Path


def is_pi(arguments):
    if not arguments:
        return False
    executable = Path(arguments[0]).name
    if executable == "pi":
        return True
    if executable not in ("node", "nodejs"):
        return False
    for argument in arguments[1:]:
        if argument.startswith("-"):
            continue
        if Path(argument).name == "pi":
            return True
        return "/@earendil-works/pi-coding-agent/" in argument and argument.endswith("/cli.js")
    return False


def main():
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            arguments = (entry / "cmdline").read_bytes().decode(errors="replace").split("\0")
        except FileNotFoundError:
            continue
        if is_pi([argument for argument in arguments if argument]):
            print("busy")
            return
    print("idle")


if __name__ == "__main__":
    main()
