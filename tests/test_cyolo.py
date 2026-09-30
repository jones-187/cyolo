#!/usr/bin/env python3
import json
import os
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
ENTRY = ROOT / "bin" / "cyolo"

FAKE_DOCKER = r'''#!/usr/bin/env python3
import json, os, sys
state = json.loads(os.environ["FAKE_DOCKER_STATE"])
argv = sys.argv[1:]
previous = 0
if os.path.exists(os.environ["FAKE_DOCKER_LOG"]):
    previous = sum(1 for line in open(os.environ["FAKE_DOCKER_LOG"], encoding="utf-8") if "python3" in line)
with open(os.environ["FAKE_DOCKER_LOG"], "a", encoding="utf-8") as f:
    f.write(json.dumps(argv, ensure_ascii=False) + "\n")
if argv[:1] == ["info"]:
    raise SystemExit(0)
if argv[:2] == ["image", "inspect"]:
    raise SystemExit(0 if state.get("image", True) else 1)
if argv and argv[0] == "compose":
    with open(os.environ["FAKE_DOCKER_LOG"], "a", encoding="utf-8") as f:
        f.write(json.dumps(["__compose_env__", os.environ.get("MODSEARCH_PACKAGE_DIR", "")]) + "\n")
    raise SystemExit(state.get("compose_status", 0))
if argv[:2] == ["container", "inspect"]:
    if not state.get("container", True): raise SystemExit(1)
    print(state.get("state", "running")); raise SystemExit(0)
if argv[:3] == ["container", "ls", "-a"]:
    if state.get("container", True): print("pi_yolo_env")
    raise SystemExit(0)
if argv[:1] == ["start"]: raise SystemExit(state.get("start_status", 0))
if argv[:1] == ["exec"]:
    if state.get("exec_status", 0): raise SystemExit(state["exec_status"])
    if "pi" in argv and "--version" in argv: print("pi " + state.get("container_version", "0.99.1"))
    elif "python3" in argv and "-" in argv:
        if state.get("process_check_status", 0): raise SystemExit(state["process_check_status"])
        checks = state.get("process_checks", [])
        print(checks[previous] if previous < len(checks) else ("busy" if state.get("processes", "") else "idle"))
    raise SystemExit(0)
raise SystemExit(64)
'''


class CyoloCliTests(unittest.TestCase):
    def run_cli(self, cwd, *args, state=None, extra_env=None, host_home=None, temp_dir=None):
        state = {"image": True, "container": True, "state": "running", **(state or {})}
        with tempfile.TemporaryDirectory(dir=temp_dir) as td:
            td = pathlib.Path(td); tools = td / "tools"; tools.mkdir()
            docker = tools / "docker"; docker.write_text(FAKE_DOCKER, encoding="utf-8"); docker.chmod(0o755)
            pi = tools / "pi"; pi.write_text("#!/bin/sh\nprintf '%s\\n' 'pi 0.99.1'\n", encoding="utf-8"); pi.chmod(0o755)
            log = td / "docker.jsonl"; home = pathlib.Path(host_home) if host_home else td / "home"; (home / "projects").mkdir(parents=True, exist_ok=True)
            package = home / "modsearch-package"; (package / "dist").mkdir(parents=True, exist_ok=True)
            (package / "dist" / "main.js").write_text("// fixture\n", encoding="utf-8")
            skill = home / ".agents" / "skills"; skill.mkdir(parents=True, exist_ok=True)
            if not (skill / "modsearch").exists() and not (skill / "modsearch").is_symlink():
                (skill / "modsearch").symlink_to(package / "skills" / "modsearch", target_is_directory=True)
            (package / "skills" / "modsearch").mkdir(parents=True, exist_ok=True)
            (home / ".modsearch").mkdir(exist_ok=True)
            env = {
                "PATH": f"{tools}:/usr/bin:/bin", "HOME": str(home), "HOST_USER": "tester",
                "HOST_UID": "1001", "HOST_GID": "1001", "FAKE_DOCKER_STATE": json.dumps(state),
                "FAKE_DOCKER_LOG": str(log), "CYolo_SECRET": "line one\nline two 'quoted'",
                "SHLVL": "42", "PI_CODING_AGENT_DIR": "/private/pi",
                "PI_CODING_AGENT_SESSION_DIR": "/private/session",
            }; env.update(extra_env or {})
            (home / "app" / "claude-docker").mkdir(parents=True, exist_ok=True)
            (home / "app" / "codex-docker").mkdir(parents=True, exist_ok=True)
            result = subprocess.run([str(ENTRY), *args], cwd=cwd, env=env, text=True, capture_output=True)
            calls = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()] if log.exists() else []
            return result, calls

    def test_project_root_and_deep_subdirectory_keep_physical_cwd(self):
        with tempfile.TemporaryDirectory(dir="/dev/shm") as td:
            home = pathlib.Path(td) / "home"
            for project in (home / "projects", home / "projects" / "demo" / "a" / "b"):
                project.mkdir(parents=True, exist_ok=True)
                result, calls = self.run_cli(project, "pi", host_home=home, temp_dir="/tmp")
                self.assertEqual(result.returncode, 0, result.stderr)
                call = next(c for c in calls if c[:1] == ["exec"] and "-it" in c)
                self.assertEqual(call[call.index("--workdir") + 1], str(project))

            sibling = home / "projects-other"
            sibling.mkdir()
            result, calls = self.run_cli(sibling, "pi", host_home=home, temp_dir="/tmp")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("没有固定映射", result.stderr)
            self.assertFalse(any(c[:1] == ["exec"] for c in calls))

    def test_path_boundary_and_unmapped_directory(self):
        with tempfile.TemporaryDirectory(dir="/dev/shm") as td:
            result, calls = self.run_cli(td, "pi")
        self.assertNotEqual(result.returncode, 0); self.assertIn("没有固定映射", result.stderr)
        self.assertFalse(any(c[:1] == ["exec"] for c in calls))

    def test_arguments_and_wrapper_flags_are_byte_preserving(self):
        with tempfile.TemporaryDirectory() as td:
            project = pathlib.Path(td) / "home" / "projects" / "demo"; project.mkdir(parents=True)
            values = ["--model", "a b", "line\none", "quote'\"", "--flag"]
            result, calls = self.run_cli(project, "pi", "--allow-version-mismatch", "--", *values)
        self.assertEqual(result.returncode, 0, result.stderr)
        call = next(c for c in calls if c[:1] == ["exec"] and "-it" in c)
        self.assertEqual(call[-len(values):], values)

    def test_bare_command_defaults_to_pi(self):
        with tempfile.TemporaryDirectory() as td:
            result, calls = self.run_cli(td)
        self.assertEqual(result.returncode, 0, result.stderr)
        call = next(c for c in calls if c[:1] == ["exec"] and "-it" in c); self.assertEqual(call[-1], "pi")

    def test_running_container_does_not_compose_up(self):
        with tempfile.TemporaryDirectory() as td: result, calls = self.run_cli(td, "pi", state={"state": "running"})
        self.assertEqual(result.returncode, 0, result.stderr); self.assertFalse(any(c[:1] == ["compose"] for c in calls))

    def test_stopped_container_is_started(self):
        with tempfile.TemporaryDirectory() as td: result, calls = self.run_cli(td, "pi", state={"state": "exited"})
        self.assertEqual(result.returncode, 0, result.stderr); self.assertIn(["start", "pi_yolo_env"], calls)

    def test_missing_image_explains_build_command(self):
        with tempfile.TemporaryDirectory() as td: result, calls = self.run_cli(td, "pi", state={"image": False, "container": False})
        self.assertNotEqual(result.returncode, 0); self.assertIn("cyolo pi --build", result.stderr)
        self.assertFalse(any(c[:1] == ["compose"] for c in calls))

    def test_version_mismatch_gives_update_and_emergency_commands(self):
        with tempfile.TemporaryDirectory() as td: result, _ = self.run_cli(td, "pi", state={"container_version": "0.98.0"})
        self.assertNotEqual(result.returncode, 0); self.assertIn("cyolo pi --build", result.stderr)
        self.assertIn("cyolo pi --allow-version-mismatch", result.stderr)

    def test_allow_version_mismatch_runs_with_existing_different_pi(self):
        with tempfile.TemporaryDirectory() as td:
            result, calls = self.run_cli(td, "pi", "--allow-version-mismatch", state={"container_version": "0.98.0"})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(any(c[:1] == ["exec"] and "-it" in c for c in calls))

    def test_allow_version_mismatch_does_not_hide_missing_pi(self):
        with tempfile.TemporaryDirectory() as td:
            result, _ = self.run_cli(td, "pi", "--allow-version-mismatch", state={"container_version": "0.98.0", "exec_status": 127})
        self.assertNotEqual(result.returncode, 0)

    def test_build_failure_does_not_start_or_exec(self):
        with tempfile.TemporaryDirectory() as td: result, calls = self.run_cli(td, "pi", "--build", state={"container": False, "compose_status": 7})
        self.assertNotEqual(result.returncode, 0); self.assertFalse(any(c[:1] == ["start"] for c in calls))
        self.assertFalse(any(c[:1] == ["exec"] and "-it" in c for c in calls))
        self.assertFalse(any(c[:1] == ["compose"] and "up" in c for c in calls))

    def test_build_receives_resolved_modsearch_package_directory(self):
        with tempfile.TemporaryDirectory() as td:
            result, calls = self.run_cli(td, "pi", "--build", state={"container": False})
        self.assertEqual(result.returncode, 0, result.stderr)
        env_calls = [c for c in calls if c[:1] == ["__compose_env__"]]
        self.assertTrue(env_calls)
        self.assertTrue(env_calls[0][1].endswith("/modsearch-package"))

    def test_idle_before_build_then_busy_before_replace_rejects_compose_up(self):
        with tempfile.TemporaryDirectory() as td:
            result, calls = self.run_cli(td, "pi", "--build", state={"process_checks": ["idle", "busy"]})
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(any(c[:1] == ["compose"] and "up" in c for c in calls))

    def test_running_pi_rejects_build(self):
        with tempfile.TemporaryDirectory() as td: result, calls = self.run_cli(td, "pi", "--build", state={"processes": "123 node /usr/bin/pi"})
        self.assertNotEqual(result.returncode, 0); self.assertIn("拒绝更新", result.stderr)
        self.assertFalse(any(c[:1] == ["compose"] for c in calls))

    def test_process_check_failure_rejects_build(self):
        with tempfile.TemporaryDirectory() as td: result, calls = self.run_cli(td, "pi", "--build", state={"process_check_status": 2})
        self.assertNotEqual(result.returncode, 0); self.assertIn("无法可靠检查", result.stderr)
        self.assertFalse(any(c[:1] == ["compose"] for c in calls))

    def test_environment_uses_names_without_values_and_filters_runtime_names(self):
        with tempfile.TemporaryDirectory() as td: result, calls = self.run_cli(td, "pi")
        self.assertEqual(result.returncode, 0, result.stderr)
        call = next(c for c in calls if c[:1] == ["exec"] and "-it" in c)
        names = [call[i + 1] for i, item in enumerate(call[:-1]) if item == "--env"]
        self.assertIn("CYolo_SECRET", names)
        for forbidden in ("HOME", "PATH", "SHLVL", "PI_CODING_AGENT_DIR", "PI_CODING_AGENT_SESSION_DIR"): self.assertNotIn(forbidden, names)
        rendered = json.dumps(calls, ensure_ascii=False); self.assertNotIn("line one", rendered); self.assertNotIn("line two", rendered)

    def test_deprecated_entries_warn_and_use_old_compose(self):
        for name in ("cc", "cx"):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as td: result, calls = self.run_cli(td, name, "--help")
            self.assertEqual(result.returncode, 0, result.stderr); self.assertIn("停止维护", result.stderr)
            self.assertTrue(any(c[:1] == ["compose"] and "up" in c for c in calls))
            old_exec = next(c for c in calls if c[:1] == ["exec"])
            self.assertTrue("claude_yolo_env" in old_exec or "codex_yolo_env" in old_exec)
            self.assertTrue(any("YOLO" in item or "dangerously" in item for item in old_exec))
            self.assertFalse(any(c[:1] == ["image"] for c in calls))


if __name__ == "__main__": unittest.main()
