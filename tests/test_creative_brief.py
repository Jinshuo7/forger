from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "plugins/forger/skills/forge-video/scripts/forge_video.py"
SPEC = importlib.util.spec_from_file_location("forge_video", SCRIPT)
forge_video = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(forge_video)


class CreativeBriefTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.project = Path(forge_video.create_project(Path(self.temp.name), "Moon Bakery")["projectPath"])

    def tearDown(self) -> None:
        self.temp.cleanup()

    def complete_intake(self) -> None:
        rounds = (
            {"idea": "A moon bakery", "purpose": "Delight", "audience": "Families"},
            {"channel": "Reels", "duration": "15 seconds", "aspectRatio": "9:16"},
            {"language": "English", "requiredContent": "A crescent loaf", "references": "None"},
            {"constraints": "Wholly fictional"},
        )
        for answers in rounds:
            forge_video.record_intake_round(self.project, answers)

    def test_intake_rounds_are_bounded_non_repeating_and_complete(self) -> None:
        with self.assertRaisesRegex(forge_video.WorkflowError, "one and three"):
            forge_video.record_intake_round(self.project, {field: field for field in forge_video.INTAKE_FIELDS[:4]})
        result = forge_video.record_intake_round(self.project, {"idea": "A moon bakery"})
        self.assertIn("purpose", result["missingFields"])
        with self.assertRaisesRegex(forge_video.WorkflowError, "already known"):
            forge_video.record_intake_round(self.project, {"idea": "Changed"})
        with self.assertRaisesRegex(forge_video.WorkflowError, "required intake"):
            forge_video.create_creative_brief(self.project, forge_video.empty_research("not-warranted"))

    def test_fictional_brief_keeps_empty_stable_research_shape(self) -> None:
        self.complete_intake()
        result = forge_video.create_creative_brief(self.project, forge_video.empty_research("not-warranted"))
        research = result["artifact"]["research"]
        self.assertEqual(research, {
            "disposition": "not-warranted", "claims": [], "evidence": [], "inspiration": [],
            "materialContradictions": [], "contradictionResolutionState": "not-applicable",
        })
        brief = (self.project / result["artifact"]["path"]).read_text(encoding="utf-8")
        for heading in ("Research Claims", "Evidence", "Inspiration", "Material Contradictions"):
            self.assertIn(f"### {heading}", brief)

    def test_explicit_unblocked_approval_binds_revision_hash_and_time(self) -> None:
        self.complete_intake(); forge_video.create_creative_brief(self.project, forge_video.empty_research("not-warranted"))
        with self.assertRaisesRegex(forge_video.WorkflowError, "explicit Creator Approval"):
            forge_video.approve_artifact(self.project, "creative-brief", False)
        with self.assertRaisesRegex(forge_video.WorkflowError, "policy hold"):
            forge_video.approve_artifact(self.project, "creative-brief", True, ["policy hold"])
        manifest = forge_video.load_manifest(self.project)
        self.assertEqual(manifest["phase"], "creative-brief-review")
        result = forge_video.approve_artifact(self.project, "creative-brief", True)
        approval = result["approval"]
        self.assertEqual(set(approval), {"artifactId", "revision", "contentHash", "approvedAt"})
        self.assertTrue(forge_video.approval_is_current(self.project, approval))
        artifact = forge_video.find_artifact(forge_video.load_manifest(self.project), "creative-brief")
        with (self.project / artifact["path"]).open("a", encoding="utf-8") as stream:
            stream.write("Creator edit\n")
        self.assertFalse(forge_video.approval_is_current(self.project, approval))
        self.assertFalse(forge_video.project_status(self.project)["approvals"][0]["current"])

    def test_unresolved_material_contradiction_blocks_approval(self) -> None:
        self.complete_intake(); research = forge_video.empty_research("warranted")
        research["claims"] = [{"text": "Claim", "citationReferences": ["source-1"]}]
        research["materialContradictions"] = [{"id": "c1", "summary": "Conflict"}]
        research["contradictionResolutionState"] = "unresolved"
        forge_video.create_creative_brief(self.project, research)
        with self.assertRaisesRegex(forge_video.WorkflowError, "Material Contradictions"):
            forge_video.approve_artifact(self.project, "creative-brief", True)


if __name__ == "__main__": unittest.main()
