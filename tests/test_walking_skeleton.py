from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import runpy
import shutil
import socket
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
MARKETPLACE = REPO_ROOT / ".agents" / "plugins" / "marketplace.json"
PLUGIN_ROOT = REPO_ROOT / "plugins" / "forger"


def run(*command: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class EgressViolation(AssertionError):
    pass


class EgressGuard:
    """Fail closed when the invoked skill opens a socket or child process."""

    def __init__(self) -> None:
        self.triggered: list[str] = []
        self._patches: list[mock._patch] = []

    def _block(self, boundary: str):
        def blocked(*_args, **_kwargs):
            self.triggered.append(boundary)
            raise EgressViolation(f"blocked generation egress through {boundary}")

        return blocked

    def __enter__(self) -> EgressGuard:
        self._patches = [
            mock.patch.object(socket, "socket", new=self._block("socket.socket")),
            mock.patch.object(subprocess, "Popen", new=self._block("subprocess.Popen")),
        ]
        for patcher in self._patches:
            patcher.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        for patcher in reversed(self._patches):
            patcher.stop()


def invoke_under_egress_guard(script: Path, workspace: Path, name: str) -> tuple[dict, list[str]]:
    output = io.StringIO()
    argv = [str(script), "--workspace", str(workspace), "--name", name]
    with (
        EgressGuard() as guard,
        mock.patch.object(sys, "argv", argv),
        contextlib.redirect_stdout(output),
    ):
        runpy.run_path(str(script), run_name="__main__")
    return json.loads(output.getvalue()), guard.triggered


class WalkingSkeletonTest(unittest.TestCase):
    maxDiff = None

    def test_marketplace_install_exposes_one_invocable_skill(self) -> None:
        if shutil.which("codex") is None:
            self.fail("codex is required to verify marketplace installation")

        marketplace = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
        self.assertEqual(marketplace["name"], "forger-development")
        self.assertEqual(len(marketplace["plugins"]), 1)
        entry = marketplace["plugins"][0]
        self.assertEqual(entry["name"], "forger")
        self.assertEqual(entry["category"], "Creativity")
        self.assertEqual(entry["policy"], {"installation": "AVAILABLE", "authentication": "ON_INSTALL"})
        self.assertNotIn("products", entry["policy"])

        manifest = json.loads(
            (PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["name"], "forger")
        self.assertEqual(manifest["version"], "0.0.0-dev")
        self.assertEqual(manifest["interface"]["category"], "Creativity")

        with tempfile.TemporaryDirectory() as codex_home_value, tempfile.TemporaryDirectory() as workspace_value:
            env = os.environ.copy()
            env["CODEX_HOME"] = codex_home_value
            added = json.loads(run("codex", "plugin", "marketplace", "add", str(REPO_ROOT), "--json", env=env).stdout)
            self.assertEqual(added["marketplaceName"], "forger-development")
            installed = json.loads(run("codex", "plugin", "add", "forger@forger-development", "--json", env=env).stdout)
            installed_root = Path(installed["installedPath"])

            skills = list(installed_root.glob("skills/*/SKILL.md"))
            self.assertEqual([skill.parent.name for skill in skills], ["forge-video"])
            script = skills[0].parent / "scripts" / "forge_video.py"
            self.assertTrue(script.is_file())

            workspace = Path(workspace_value)
            first, first_egress = invoke_under_egress_guard(script, workspace, "Neon Walk")
            first_path = Path(first["projectPath"])
            first_snapshot = {path.relative_to(first_path): file_hash(path) for path in first_path.rglob("*") if path.is_file()}

            second, second_egress = invoke_under_egress_guard(script, workspace, "Neon Walk")
            second_path = Path(second["projectPath"])

            self.assertEqual(first_path.name, "neon-walk")
            self.assertEqual(second_path.name, "neon-walk-2")
            self.assertNotEqual(first_path, second_path)
            self.assertEqual(
                {path.name for path in (workspace / "forger-projects").iterdir()},
                {"neon-walk", "neon-walk-2"},
            )
            self.assertEqual(
                first_snapshot,
                {path.relative_to(first_path): file_hash(path) for path in first_path.rglob("*") if path.is_file()},
            )
            for project_path in (first_path, second_path):
                self.assertEqual(
                    {path.relative_to(project_path) for path in project_path.rglob("*") if path.is_file()},
                    {Path("forger.project.json")},
                )
                manifest = json.loads((project_path / "forger.project.json").read_text(encoding="utf-8"))
                self.assertEqual(manifest["phase"], "walking-skeleton")
                self.assertNotIn("artifacts", manifest)

            self.assertNotIn("generationEvents", first)
            self.assertNotIn("generationEvents", second)
            self.assertEqual(first_egress, [])
            self.assertEqual(second_egress, [])
            self.assertEqual(
                {path.name for path in workspace.iterdir()},
                {"forger-projects"},
            )

    def test_egress_guard_rejects_deliberate_outbound_calls(self) -> None:
        offenders = (
            ("socket.socket", lambda: socket.socket()),
            (
                "subprocess.Popen",
                lambda: subprocess.run([sys.executable, "-c", "pass"], check=True),
            ),
        )
        for boundary, offend in offenders:
            with self.subTest(boundary=boundary):
                with EgressGuard() as guard:
                    with self.assertRaisesRegex(EgressViolation, boundary.replace(".", r"\.")):
                        offend()
                self.assertEqual(guard.triggered, [boundary])


if __name__ == "__main__":
    unittest.main()
