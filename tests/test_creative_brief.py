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

    def create_fictional_brief(self) -> dict:
        self.complete_intake()
        return forge_video.create_creative_brief(
            self.project, forge_video.empty_research("not-warranted")
        )

    def test_intake_script_enforces_bounded_rounds_known_fields_and_completion(self) -> None:
        with self.assertRaisesRegex(forge_video.WorkflowError, "one and three"):
            forge_video.record_intake_round(self.project, {field: field for field in forge_video.INTAKE_FIELDS[:4]})
        result = forge_video.record_intake_round(self.project, {"idea": "A moon bakery"})
        self.assertIn("purpose", result["missingFields"])
        with self.assertRaisesRegex(forge_video.WorkflowError, "already known"):
            forge_video.record_intake_round(self.project, {"idea": "Changed"})
        with self.assertRaisesRegex(forge_video.WorkflowError, "required intake"):
            forge_video.create_creative_brief(self.project, forge_video.empty_research("not-warranted"))

    def test_intake_accepts_minutes_expressed_durations(self) -> None:
        fixtures = {
            "1 minute": 60.0,
            "1m30s": 90.0,
            "1:30": 90.0,
        }
        for duration, expected_seconds in fixtures.items():
            with self.subTest(duration=duration):
                project = Path(
                    forge_video.create_project(
                        Path(self.temp.name), f"Duration {duration}"
                    )["projectPath"]
                )
                forge_video.record_intake_round(project, {"duration": duration})
                recorded = forge_video.load_manifest(project)["intake"]["answers"]["duration"]
                self.assertEqual(recorded, duration)
                self.assertEqual(
                    forge_video.parse_duration_seconds(recorded), expected_seconds
                )

    def test_intake_rejects_unparseable_and_out_of_scope_durations(self) -> None:
        for duration in ("soon", "4 seconds", "181 seconds"):
            with self.subTest(duration=duration):
                project = Path(
                    forge_video.create_project(
                        Path(self.temp.name), f"Invalid duration {duration}"
                    )["projectPath"]
                )
                with self.assertRaisesRegex(forge_video.WorkflowError, "duration"):
                    forge_video.record_intake_round(project, {"duration": duration})
                self.assertNotIn(
                    "duration",
                    forge_video.load_manifest(project)["intake"]["answers"],
                )

    def test_explicit_not_warranted_disposition_produces_reviewable_creative_brief(self) -> None:
        result = self.create_fictional_brief()
        self.assertEqual(result["artifact"]["research"]["disposition"], "not-warranted")
        self.assertTrue((self.project / result["artifact"]["path"]).is_file())

    def test_creative_brief_uses_stable_optional_research_field_shape(self) -> None:
        result = self.create_fictional_brief()
        research = result["artifact"]["research"]
        self.assertEqual(research, {
            "disposition": "not-warranted", "claims": [], "evidence": [], "inspiration": [],
            "materialContradictions": [], "contradictionResolutionState": "not-applicable",
        })
        brief = (self.project / result["artifact"]["path"]).read_text(encoding="utf-8")
        for heading in ("Research Claims", "Evidence", "Inspiration", "Material Contradictions"):
            self.assertIn(f"### {heading}", brief)

    def test_creative_brief_milestone_advances_only_after_explicit_creator_approval(self) -> None:
        self.create_fictional_brief()
        with self.assertRaisesRegex(forge_video.WorkflowError, "explicit Creator Approval"):
            forge_video.approve_artifact(self.project, "creative-brief", False)
        self.assertEqual(forge_video.load_manifest(self.project)["phase"], "creative-brief-review")
        result = forge_video.approve_artifact(self.project, "creative-brief", True)
        self.assertEqual(result["phase"], "creative-direction")
        self.assertEqual(
            forge_video.load_manifest(self.project)["milestones"]["creativeBrief"], "approved"
        )

    def test_approval_binds_artifact_revision_hash_and_time_until_both_match(self) -> None:
        first = self.create_fictional_brief()["artifact"]
        result = forge_video.approve_artifact(self.project, "creative-brief", True)
        approval = result["approval"]
        self.assertEqual(set(approval), {"artifactId", "revision", "contentHash", "approvedAt"})
        self.assertTrue(forge_video.approval_is_current(self.project, approval))
        artifact = forge_video.find_artifact(forge_video.load_manifest(self.project), "creative-brief")
        self.assertEqual(artifact["revisionState"], "current")
        self.assertNotIn("status", artifact)
        artifact_path = self.project / artifact["path"]
        original_content = artifact_path.read_text(encoding="utf-8")
        artifact_path.write_text(original_content + "Creator edit\n", encoding="utf-8")
        self.assertFalse(forge_video.approval_is_current(self.project, approval))
        artifact_path.write_text(original_content, encoding="utf-8")
        self.assertTrue(forge_video.approval_is_current(self.project, approval))

        second = forge_video.create_creative_brief(
            self.project, forge_video.empty_research("not-warranted")
        )["artifact"]
        self.assertEqual(first["contentHash"], second["contentHash"])
        self.assertEqual(approval["contentHash"], second["contentHash"])
        self.assertEqual(second["currentRevision"], first["currentRevision"] + 1)
        self.assertNotEqual(approval["revision"], second["currentRevision"])
        self.assertFalse(forge_video.approval_is_current(self.project, approval))

    def test_approval_path_advances_only_when_general_blocker_set_is_empty(self) -> None:
        self.create_fictional_brief()
        with self.assertRaisesRegex(forge_video.WorkflowError, "policy hold"):
            forge_video.approve_artifact(self.project, "creative-brief", True, ["policy hold"])
        self.assertEqual(forge_video.load_manifest(self.project)["phase"], "creative-brief-review")
        research = forge_video.empty_research("warranted")
        research["claims"] = [{"text": "Claim", "citationReferences": ["source-1"]}]
        research["materialContradictions"] = [{"id": "c1", "summary": "Conflict"}]
        research["contradictionResolutionState"] = "unresolved"
        forge_video.create_creative_brief(self.project, research)
        with self.assertRaisesRegex(forge_video.WorkflowError, "Material Contradictions"):
            forge_video.approve_artifact(self.project, "creative-brief", True)

    def test_warranted_research_defaults_unresolved_and_rejects_unknown_state(self) -> None:
        research = forge_video.empty_research("warranted")
        self.assertEqual(research["contradictionResolutionState"], "unresolved")
        research["contradictionResolutionState"] = "assumed-resolved"
        with self.assertRaisesRegex(forge_video.WorkflowError, "invalid contradiction resolution state"):
            forge_video.validate_research(research)


if __name__ == "__main__": unittest.main()
