import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


def _manage_path() -> Path | None:
    candidates = []
    configured = os.environ.get("ZENTAO_MANAGE_PATH")
    if configured:
        candidates.append(Path(configured))
    candidates.append(Path("/home/jones/projects/skills/skills/zentao-bug-ops/scripts/manage.py"))
    return next((path for path in candidates if path.is_file()), None)


MANAGE_PATH = _manage_path()


@unittest.skipUnless(MANAGE_PATH is not None, "zentao manage.py is not available")
class ZentaoRegistrationTest(unittest.TestCase):
    def test_install_re_registers_old_absolute_node_and_keeps_node_registration(self):
        assert MANAGE_PATH is not None
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fake_bin = root / "bin"
            fake_bin.mkdir()
            state_path = root / "registration.json"
            log_path = root / "codex.log"
            fake_node = fake_bin / "node"
            fake_node.write_text(
                """#!/usr/bin/env python3
import json
import sys

if len(sys.argv) > 1 and sys.argv[1] == '--version':
    print('v24.18.0')
    raise SystemExit(0)

for line in sys.stdin:
    message = json.loads(line)
    if message.get('method') == 'initialize':
        print(json.dumps({'jsonrpc': '2.0', 'id': message.get('id'), 'result': {}}), flush=True)
    elif message.get('method') == 'tools/list':
        tools = [{'name': name} for name in ('createBug', 'resolveBug', 'getMyUnresolvedBugs')]
        print(json.dumps({'jsonrpc': '2.0', 'id': message.get('id'), 'result': {'tools': tools}}), flush=True)
"""
            )
            fake_node.chmod(0o755)
            fake_npm = fake_bin / "npm"
            fake_npm.write_text(
                """#!/usr/bin/env python3
from pathlib import Path
import sys

if sys.argv[1:] == ['install']:
    raise SystemExit(0)
if sys.argv[1:] == ['run', 'build']:
    Path('dist').mkdir(exist_ok=True)
    Path('dist/index.js').touch()
"""
            )
            fake_npm.chmod(0o755)
            fake_codex = fake_bin / "codex"
            fake_codex.write_text(
                """#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

state_path = Path(os.environ['FAKE_CODEX_STATE'])
log_path = Path(os.environ['FAKE_CODEX_LOG'])
args = sys.argv[1:]
if args[:3] == ['mcp', 'get', 'zentao-bug-ops']:
    if not state_path.exists():
        print('No MCP server named zentao-bug-ops', file=sys.stderr)
        raise SystemExit(1)
    print(state_path.read_text())
elif args[:3] == ['mcp', 'add', 'zentao-bug-ops']:
    separator = args.index('--')
    command = args[separator + 1]
    server = args[separator + 2]
    log_path.open('a').write(json.dumps(args) + '\\n')
    state_path.write_text(json.dumps({'enabled': True, 'transport': {'type': 'stdio', 'command': command, 'args': [server], 'env_vars': ['ZENTAO_URL', 'ZENTAO_USERNAME', 'ZENTAO_PASSWORD']}, 'enabled_tools': ['createBug', 'resolveBug', 'getMyUnresolvedBugs']}))
else:
    raise SystemExit(2)
"""
            )
            fake_codex.chmod(0o755)

            server_path = root / ".local/share/zentao-bug-ops-mcp/dist/index.js"
            state_path.write_text(
                json.dumps(
                    {
                        "enabled": True,
                        "transport": {
                            "type": "stdio",
                            "command": str(fake_node),
                            "args": [str(server_path)],
                            "env_vars": ["ZENTAO_URL", "ZENTAO_USERNAME", "ZENTAO_PASSWORD"],
                        },
                        "enabled_tools": ["createBug", "resolveBug", "getMyUnresolvedBugs"],
                    }
                )
            )
            environment = os.environ.copy()
            environment.update(
                {
                    "HOME": str(root),
                    "PATH": f"{fake_bin}{os.pathsep}{os.environ.get('PATH', '')}",
                    "FAKE_CODEX_STATE": str(state_path),
                    "FAKE_CODEX_LOG": str(log_path),
                    "ZENTAO_URL": "https://example.invalid",
                    "ZENTAO_USERNAME": "test-user",
                    "ZENTAO_PASSWORD": "test-password",
                }
            )
            config = root / ".codex/config.toml"
            config.parent.mkdir(parents=True)
            config.write_text('[mcp_servers.zentao-bug-ops]\ncommand = "node"\n')

            first = subprocess.run(
                [sys.executable, str(MANAGE_PATH), "install"],
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            self.assertEqual(json.loads(state_path.read_text())["transport"]["command"], "node")

            second = subprocess.run(
                [sys.executable, str(MANAGE_PATH), "install"],
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
            registrations = log_path.read_text().splitlines()
            self.assertEqual(len(registrations), 1)
            self.assertEqual(json.loads(registrations[0])[-2], "node")


if __name__ == "__main__":
    unittest.main()
