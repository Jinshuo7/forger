from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


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


def load_walking_skeleton(script: Path):
    spec = importlib.util.spec_from_file_location("forger_walking_skeleton", script)
    if spec is None or spec.loader is None:
        raise AssertionError(f"could not load {script}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
            first = json.loads(
                run(
                    "python3",
                    str(script),
                    "--workspace",
                    str(workspace),
                    "--name",
                    "Neon Walk",
                ).stdout
            )
            first_path = Path(first["projectPath"])
            first_snapshot = {path.relative_to(first_path): file_hash(path) for path in first_path.rglob("*") if path.is_file()}

            second = json.loads(
                run(
                    "python3",
                    str(script),
                    "--workspace",
                    str(workspace),
                    "--name",
                    "Neon Walk",
                ).stdout
            )
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

            self.assertEqual(first["generationEvents"], [])
            self.assertEqual(second["generationEvents"], [])
            self.assertEqual(
                {path.name for path in workspace.iterdir()},
                {"forger-projects"},
            )

    def test_boundary_monitor_rejects_any_generation(self) -> None:
        script = PLUGIN_ROOT / "skills" / "forge-video" / "scripts" / "forge_video.py"
        module = load_walking_skeleton(script)
        for event_name in (
            module.GenerationMonitor.KEYFRAME_EVENT,
            module.GenerationMonitor.FINAL_VIDEO_EVENT,
        ):
            with self.subTest(event=event_name):
                monitor = module.GenerationMonitor()
                monitor.observe({"event": event_name})
                with self.assertRaisesRegex(AssertionError, "crossed a generation boundary"):
                    monitor.assert_none_crossed()


if __name__ == "__main__":
    unittest.main()
