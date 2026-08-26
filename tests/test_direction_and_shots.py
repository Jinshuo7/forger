from __future__ import annotations

import importlib.util
import hashlib
import tempfile
import unittest
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "plugins/forger/skills/forge-video/scripts/forge_video.py"
SPEC = importlib.util.spec_from_file_location("forge_video_direction_shots", SCRIPT)
forge_video = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(forge_video)


class DirectionAndShotTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.project = Path(
            forge_video.create_project(Path(self.temp.name), "Moon Bakery")["projectPath"]
        )
        rounds = (
            {"idea": "A moon bakery", "purpose": "Delight", "audience": "Families"},
            {"channel": "Reels", "duration": "15 seconds", "aspectRatio": "9:16"},
            {"language": "English", "requiredContent": "A crescent loaf", "references": "None"},
            {"constraints": "Wholly fictional"},
        )
        for answers in rounds:
            forge_video.record_intake_round(self.project, answers)
        forge_video.create_creative_brief(
            self.project, forge_video.empty_research("not-warranted")
        )
        forge_video.approve_artifact(self.project, "creative-brief", True)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def directions(self) -> list[dict]:
        return [
            {
                "id": "direction-wonder",
                "title": "Oven of Wonder",
                "recommended": True,
                "narrativeAxis": "A child follows a loaf from stardust to breakfast.",
                "aestheticAxis": "Warm miniature stop-motion with tactile flour textures.",
            },
            {
                "id": "direction-heist",
                "title": "Midnight Crumb Heist",
                "recommended": False,
                "narrativeAxis": "Mice execute a comic caper to steal the crescent loaf.",
                "aestheticAxis": "High-contrast noir silhouettes with graphic spot color.",
            },
            {
                "id": "direction-ritual",
                "title": "Celestial Ritual",
                "recommended": False,
                "narrativeAxis": "Bakers perform a quiet ritual that wakes the moon.",
                "aestheticAxis": "Symmetrical silver-blue tableaux with slow ceremonial motion.",
            },
        ]

    def creative_direction_artifacts(self, manifest: dict) -> list[dict]:
        return [
            artifact for artifact in manifest["artifacts"]
            if artifact["type"] == "creative-direction"
        ]

    def select_and_approve_direction(self) -> dict:
        forge_video.create_creative_directions(self.project, self.directions())
        forge_video.select_creative_direction(
            self.project,
            "direction-wonder",
            {
                "direction-heist": "Comedy undercuts the sense of wonder.",
                "direction-ritual": "Too restrained for the channel.",
            },
        )
        return forge_video.approve_artifact(self.project, "direction-wonder", True)

    def select_direction_at_revision_two(self) -> None:
        forge_video.create_creative_directions(self.project, self.directions())
        forge_video.create_creative_directions(self.project, self.directions())
        forge_video.select_creative_direction(
            self.project,
            "direction-wonder",
            {
                "direction-heist": "Comedy undercuts the sense of wonder.",
                "direction-ritual": "Too restrained for the channel.",
            },
        )

    def reference_bible(self) -> list[dict]:
        return [
            {"id": "character-baker", "type": "character", "name": "Mina the baker"},
            {"id": "prop-crescent-loaf", "type": "prop", "name": "Crescent loaf"},
            {"id": "location-moon-bakery", "type": "location", "name": "Moon bakery"},
        ]

    def shots(self) -> list[dict]:
        common = {
            "composition": "Layered foreground and background",
            "framing": "Medium-wide 35mm equivalent",
            "cameraMotion": "Slow push in",
            "subjectAction": "Mina works the dough",
            "lighting": "Warm oven key with cool moon fill",
            "continuity": "Crescent loaf remains flour-dusted",
            "transition": "Match cut on the crescent shape",
            "audio": "Soft room tone and oven crackle",
            "dialogue": "",
            "captions": "",
            "editNotes": "Cut on action",
            "visualBoardReferences": [],
            "referenceBibleEntityIds": ["character-baker", "prop-crescent-loaf"],
        }
        return [
            {**common, "id": "shot-1", "durationSeconds": 5.0, "purpose": "Establish the bakery"},
            {**common, "id": "shot-2", "durationSeconds": 5.0, "purpose": "Reveal the crescent loaf"},
            {**common, "id": "shot-3", "durationSeconds": 5.0, "purpose": "Land the breakfast payoff"},
        ]

    def test_three_directions_have_one_recommendation_and_unique_nonempty_axes(self) -> None:
        result = forge_video.create_creative_directions(self.project, self.directions())
        self.assertEqual(len(result["directions"]), 3)
        self.assertEqual(sum(d["recommended"] for d in result["directions"]), 1)
        self.assertEqual(
            len({(d["narrativeAxis"], d["aestheticAxis"]) for d in result["directions"]}),
            3,
        )
        self.assertTrue(all(d["narrativeAxis"] and d["aestheticAxis"] for d in result["directions"]))
        brief = forge_video.find_artifact(
            forge_video.load_manifest(self.project), "creative-brief"
        )
        for direction in result["directions"]:
            self.assertEqual(
                direction["dependencies"],
                [{"artifactId": "creative-brief", "revision": brief["currentRevision"]}],
            )
        self.assertEqual(
            len([
                artifact for artifact in forge_video.load_manifest(self.project)["artifacts"]
                if artifact["type"] == "creative-direction"
            ]),
            3,
        )

    def test_direction_contract_gate_rejects_a_real_duplicate_axis_violation(self) -> None:
        directions = self.directions()
        directions[2]["narrativeAxis"] = directions[1]["narrativeAxis"]
        directions[2]["aestheticAxis"] = directions[1]["aestheticAxis"]
        with self.assertRaisesRegex(forge_video.WorkflowError, "narrative and aesthetic axes"):
            forge_video.create_creative_directions(self.project, directions)
        self.assertNotIn("creativeDirections", forge_video.load_manifest(self.project))

    def test_direction_contract_rejects_slug_collisions_before_writing_artifacts(self) -> None:
        directions = self.directions()
        directions[0]["id"] = "direction-wonder"
        directions[1]["id"] = "direction_wonder"

        with self.assertRaisesRegex(
            forge_video.WorkflowError,
            "Creative Direction ids must produce unique artifact paths",
        ):
            forge_video.create_creative_directions(self.project, directions)

        manifest = forge_video.load_manifest(self.project)
        self.assertEqual(self.creative_direction_artifacts(manifest), [])
        artifact_dir = self.project / "artifacts" / "creative-directions"
        self.assertEqual(list(artifact_dir.glob("*.md")), [])

    def test_direction_contract_gate_meta_test_drives_each_cardinality_marker_and_axis_violation(self) -> None:
        fixtures = []
        fixtures.append(("exactly three", self.directions()[:2]))
        no_recommendation = self.directions()
        no_recommendation[0]["recommended"] = False
        fixtures.append(("exactly one", no_recommendation))
        two_recommendations = self.directions()
        two_recommendations[1]["recommended"] = True
        fixtures.append(("exactly one", two_recommendations))
        empty_axis = self.directions()
        empty_axis[0]["narrativeAxis"] = ""
        fixtures.append((
            "narrative and aesthetic axes must be non-empty",
            empty_axis,
        ))
        for message, directions in fixtures:
            with self.subTest(message=message):
                with self.assertRaisesRegex(forge_video.WorkflowError, message):
                    forge_video.create_creative_directions(self.project, directions)

    def test_selection_preserves_rejections_and_requires_an_explicit_selection_call(self) -> None:
        forge_video.create_creative_directions(self.project, self.directions())
        forge_video.select_creative_direction(
            self.project,
            "direction-wonder",
            {
                "direction-heist": "Comedy undercuts the sense of wonder.",
                "direction-ritual": "Too restrained for the channel.",
            },
        )
        manifest = forge_video.load_manifest(self.project)
        self.assertNotIn("creativeDirections", manifest)
        directions = self.creative_direction_artifacts(manifest)
        rejected = {
            d["id"]: d["rejectionHistory"] for d in directions
            if d["selectionState"] == "rejected"
        }
        self.assertEqual(set(rejected), {"direction-heist", "direction-ritual"})
        self.assertEqual(rejected["direction-heist"][0]["reason"], "Comedy undercuts the sense of wonder.")

        # Regeneration cannot silently select a rejected direction.
        forge_video.create_creative_directions(self.project, self.directions())
        manifest = forge_video.load_manifest(self.project)
        self.assertNotIn("creativeDirections", manifest)
        directions = self.creative_direction_artifacts(manifest)
        self.assertEqual(manifest["selectedCreativeDirectionId"], "direction-wonder")
        self.assertEqual(
            next(d for d in directions if d["id"] == "direction-heist")["selectionState"],
            "rejected",
        )

        # The rejected direction may be selected only through the explicit selection contract.
        forge_video.select_creative_direction(
            self.project,
            "direction-heist",
            {
                "direction-wonder": "The Creator chose a more playful revision.",
                "direction-ritual": "Still too restrained.",
            },
        )
        manifest = forge_video.load_manifest(self.project)
        directions = self.creative_direction_artifacts(manifest)
        self.assertEqual(manifest["selectedCreativeDirectionId"], "direction-heist")
        heist_history = next(
            d for d in directions if d["id"] == "direction-heist"
        )["rejectionHistory"]
        self.assertEqual(len(heist_history), 1)
        self.assertEqual(
            heist_history[0]["reason"],
            "Comedy undercuts the sense of wonder.",
        )

    def test_selection_gate_meta_test_requires_all_rejection_reasons_and_selected_approval(self) -> None:
        forge_video.create_creative_directions(self.project, self.directions())
        with self.assertRaisesRegex(forge_video.WorkflowError, "rejection reason"):
            forge_video.select_creative_direction(
                self.project,
                "direction-wonder",
                {"direction-heist": "Comedy undercuts wonder."},
            )
        self.assertNotIn("selectedCreativeDirectionId", forge_video.load_manifest(self.project))
        with self.assertRaisesRegex(forge_video.WorkflowError, "not selected"):
            forge_video.approve_artifact(self.project, "direction-heist", True)

    def test_reselection_invalidates_previous_direction_approval_and_reopens_milestone(self) -> None:
        self.select_and_approve_direction()
        before = forge_video.load_manifest(self.project)
        previously_selected_id = before["selectedCreativeDirectionId"]
        previously_selected = forge_video.find_artifact(before, previously_selected_id)
        self.assertEqual(previously_selected["selectionState"], "selected")
        previous_approval = next(
            approval for approval in before["approvals"]
            if approval["artifactId"] == previously_selected["id"]
        )
        self.assertTrue(forge_video.approval_is_current(self.project, previous_approval))
        self.assertEqual(before["milestones"]["creativeDirection"], "approved")

        forge_video.select_creative_direction(
            self.project,
            "direction-heist",
            {
                "direction-wonder": "The Creator chose a more playful direction.",
                "direction-ritual": "Still too restrained.",
            },
        )

        after = forge_video.load_manifest(self.project)
        previously_selected = forge_video.find_artifact(after, previously_selected_id)
        self.assertEqual(previously_selected["selectionState"], "rejected")
        retained_approval = next(
            approval for approval in after["approvals"]
            if approval["artifactId"] == previously_selected["id"]
        )
        self.assertFalse(forge_video.approval_is_current(self.project, retained_approval))
        self.assertLess(
            retained_approval["revision"], previously_selected["currentRevision"]
        )
        self.assertEqual(after["milestones"]["creativeDirection"], "awaiting-approval")

    def test_reapproval_preserves_every_historical_approval(self) -> None:
        first_approval = self.select_and_approve_direction()["approval"]
        forge_video.select_creative_direction(
            self.project,
            "direction-heist",
            {
                "direction-wonder": "The Creator chose a more playful direction.",
                "direction-ritual": "Still too restrained.",
            },
        )
        forge_video.select_creative_direction(
            self.project,
            "direction-wonder",
            {
                "direction-heist": "Wonder better serves the intended tone.",
                "direction-ritual": "Still too restrained.",
            },
        )
        second_approval = forge_video.approve_artifact(
            self.project, "direction-wonder", True
        )["approval"]

        approvals = [
            approval for approval in forge_video.load_manifest(self.project)["approvals"]
            if approval["artifactId"] == "direction-wonder"
        ]
        self.assertEqual(
            [approval["revision"] for approval in approvals],
            [first_approval["revision"], second_approval["revision"]],
        )
        self.assertFalse(forge_video.approval_is_current(self.project, approvals[0]))
        self.assertTrue(forge_video.approval_is_current(self.project, approvals[1]))

    def test_shot_contract_requires_every_property_and_known_reference_bible_entities(self) -> None:
        self.select_and_approve_direction()
        for required_property in forge_video.REQUIRED_SHOT_PROPERTIES:
            with self.subTest(required_property=required_property):
                shots = self.shots()
                del shots[0][required_property]
                with self.assertRaisesRegex(forge_video.WorkflowError, required_property):
                    forge_video.create_shot_sequence(
                        self.project, shots, self.reference_bible(), required_story_beat_count=3
                    )

        shots = self.shots()
        shots[0]["durationSeconds"] = "five"
        with self.assertRaisesRegex(
            forge_video.WorkflowError, "durationSeconds must be numeric"
        ):
            forge_video.create_shot_sequence(
                self.project, shots, self.reference_bible(), required_story_beat_count=3
            )

        shots = self.shots()
        shots[0]["referenceBibleEntityIds"] = ["unknown-character"]
        with self.assertRaisesRegex(forge_video.WorkflowError, "unknown Reference Bible entity"):
            forge_video.create_shot_sequence(
                self.project, shots, self.reference_bible(), required_story_beat_count=3
            )

    def test_shot_contract_rejects_all_keys_present_with_all_values_empty(self) -> None:
        self.select_and_approve_direction()
        empty_shot = {
            property_name: ""
            for property_name in forge_video.REQUIRED_SHOT_PROPERTIES
        }
        with self.assertRaisesRegex(
            forge_video.WorkflowError, "non-empty.*purpose"
        ):
            forge_video.create_shot_sequence(
                self.project,
                [empty_shot],
                self.reference_bible(),
                required_story_beat_count=1,
            )

    def test_shot_contract_requires_a_nonempty_string_id(self) -> None:
        self.select_and_approve_direction()
        shot = {
            **self.shots()[0],
            "id": "",
            "durationSeconds": 15.0,
            "purpose": "Carry the complete story in one Shot",
        }
        with self.assertRaisesRegex(
            forge_video.WorkflowError, "Shot 1 id must be a non-empty string"
        ):
            forge_video.create_shot_sequence(
                self.project,
                [shot],
                self.reference_bible(),
                required_story_beat_count=1,
            )

    def test_shot_contract_gate_meta_test_drives_a_real_missing_property_violation(self) -> None:
        self.select_and_approve_direction()
        shots = self.shots()
        del shots[1]["continuity"]
        with self.assertRaisesRegex(forge_video.WorkflowError, "continuity"):
            forge_video.create_shot_sequence(
                self.project, shots, self.reference_bible(), required_story_beat_count=3
            )
        self.assertNotIn("shot-sequence", {
            artifact["id"] for artifact in forge_video.load_manifest(self.project)["artifacts"]
        })

    def test_shot_sequence_renders_sixteen_named_markdown_fields(self) -> None:
        self.select_and_approve_direction()
        artifact = forge_video.create_shot_sequence(
            self.project, self.shots(), self.reference_bible(), required_story_beat_count=3
        )["artifact"]
        rendered = (self.project / artifact["path"]).read_text(encoding="utf-8")

        self.assertNotIn("```json", rendered)
        self.assertNotIn('"cameraMotion":', rendered)
        for expected_line in (
            "- ID: shot-1",
            "- Duration seconds: 5",
            "- Purpose: Establish the bakery",
            "- Composition: Layered foreground and background",
            "- Framing: Medium-wide 35mm equivalent",
            "- Camera motion: Slow push in",
            "- Subject action: Mina works the dough",
            "- Lighting: Warm oven key with cool moon fill",
            "- Continuity: Crescent loaf remains flour-dusted",
            "- Transition: Match cut on the crescent shape",
            "- Audio: Soft room tone and oven crackle",
            "- Dialogue: None.",
            "- Captions: None.",
            "- Edit notes: Cut on action",
            "- Visual Board references: None.",
            "- Reference Bible entity IDs: character-baker, prop-crescent-loaf",
        ):
            with self.subTest(expected_line=expected_line):
                self.assertIn(expected_line, rendered)

    def test_timing_monitor_discriminates_fixtures_and_pauses_only_shot_sequence(self) -> None:
        self.select_and_approve_direction()
        before = forge_video.load_manifest(self.project)
        before_milestones = dict(before["milestones"])
        before_approvals = {
            approval["artifactId"]: forge_video.approval_is_current(self.project, approval)
            for approval in before["approvals"]
        }
        self.assertEqual(before_approvals, {"creative-brief": True, "direction-wonder": True})

        infeasible_shots = []
        for index in range(16):
            shot = dict(self.shots()[0])
            shot.update({
                "id": f"infeasible-shot-{index + 1}",
                "durationSeconds": 15.0 / 16.0,
                "purpose": f"Required story beat {index + 1}",
            })
            infeasible_shots.append(shot)
        self.assertAlmostEqual(
            sum(shot["durationSeconds"] for shot in infeasible_shots), 15.0
        )
        with self.assertRaisesRegex(forge_video.WorkflowError, "at most 15 story beats"):
            forge_video.create_shot_sequence(
                self.project,
                infeasible_shots,
                self.reference_bible(),
                required_story_beat_count=16,
            )
        paused = forge_video.load_manifest(self.project)
        self.assertEqual(paused["milestones"]["creativeBrief"], before_milestones["creativeBrief"])
        self.assertEqual(
            paused["milestones"]["creativeDirection"], before_milestones["creativeDirection"]
        )
        self.assertEqual(paused["milestones"]["shotSequence"], "paused")
        self.assertEqual(
            {
                approval["artifactId"]: forge_video.approval_is_current(self.project, approval)
                for approval in paused["approvals"]
            },
            before_approvals,
        )

        result = forge_video.create_shot_sequence(
            self.project, self.shots(), self.reference_bible(), required_story_beat_count=3
        )
        self.assertEqual(result["timing"], {
            "briefDurationSeconds": 15.0,
            "shotDurationTotalSeconds": 15.0,
            "toleranceSeconds": forge_video.SHOT_DURATION_TOLERANCE_SECONDS,
            "minimumShotDurationSeconds": forge_video.MINIMUM_SHOT_DURATION_SECONDS,
            "requiredStoryBeatCount": 3,
        })
        self.assertEqual(
            forge_video.load_manifest(self.project)["milestones"]["shotSequence"],
            "awaiting-approval",
        )

    def test_timing_monitor_meta_test_drives_a_real_duration_sum_violation(self) -> None:
        self.select_and_approve_direction()
        shots = self.shots()
        shots[-1]["durationSeconds"] = 4.0
        with self.assertRaisesRegex(forge_video.WorkflowError, "must equal the approved Creative Brief duration"):
            forge_video.create_shot_sequence(
                self.project, shots, self.reference_bible(), required_story_beat_count=3
            )
        self.assertEqual(
            forge_video.load_manifest(self.project)["milestones"]["shotSequence"], "paused"
        )

    def test_timing_monitor_meta_test_drives_a_real_minimum_shot_violation(self) -> None:
        self.select_and_approve_direction()
        shots = self.shots()
        shots[0]["durationSeconds"] = 0.5
        shots[1]["durationSeconds"] = 9.5
        with self.assertRaisesRegex(forge_video.WorkflowError, "must be at least 1 second"):
            forge_video.create_shot_sequence(
                self.project, shots, self.reference_bible(), required_story_beat_count=3
            )
        self.assertEqual(
            forge_video.load_manifest(self.project)["milestones"]["shotSequence"], "paused"
        )

    def assert_approval_binding(self, artifact_id: str, approval: dict) -> None:
        self.assertEqual(
            set(approval), {"artifactId", "revision", "contentHash", "approvedAt"}
        )
        self.assertEqual(approval["artifactId"], artifact_id)
        datetime.fromisoformat(approval["approvedAt"].replace("Z", "+00:00"))
        self.assertTrue(forge_video.approval_is_current(self.project, approval))

        # Same content, new Revision: the revision half of the binding must fire.
        manifest = forge_video.load_manifest(self.project)
        artifact = forge_video.find_artifact(manifest, artifact_id)
        original_revision = artifact["currentRevision"]
        artifact["currentRevision"] = original_revision + 1
        forge_video.save_manifest(self.project, manifest)
        self.assertFalse(forge_video.approval_is_current(self.project, approval))

        # Same Revision, new content: the hash half of the binding must fire.
        manifest = forge_video.load_manifest(self.project)
        artifact = forge_video.find_artifact(manifest, artifact_id)
        artifact["currentRevision"] = original_revision
        artifact_path = self.project / artifact["path"]
        artifact_path.write_text(
            artifact_path.read_text(encoding="utf-8") + "\nCreator changed this Revision.\n",
            encoding="utf-8",
        )
        artifact["contentHash"] = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
        forge_video.save_manifest(self.project, manifest)
        self.assertFalse(forge_video.approval_is_current(self.project, approval))

    def test_creative_direction_approval_binds_identity_revision_hash_and_time(self) -> None:
        result = self.select_and_approve_direction()
        self.assertEqual(result["phase"], "shot-sequence")
        self.assertEqual(
            forge_video.load_manifest(self.project)["milestones"]["creativeDirection"],
            "approved",
        )
        self.assert_approval_binding("direction-wonder", result["approval"])

    def test_creative_direction_approval_records_revision_two_literally(self) -> None:
        self.select_direction_at_revision_two()
        approval = forge_video.approve_artifact(
            self.project, "direction-wonder", True
        )["approval"]
        self.assertEqual(approval["revision"], 2)

    def test_direction_dependency_gate_meta_test_rejects_a_stale_brief_approval(self) -> None:
        forge_video.create_creative_directions(self.project, self.directions())
        forge_video.select_creative_direction(
            self.project,
            "direction-wonder",
            {
                "direction-heist": "Comedy undercuts wonder.",
                "direction-ritual": "Too restrained.",
            },
        )
        manifest = forge_video.load_manifest(self.project)
        brief = forge_video.find_artifact(manifest, "creative-brief")
        original_revision = brief["currentRevision"]

        # Same content, new Revision invalidates the depended-on Approval.
        brief["currentRevision"] = original_revision + 1
        forge_video.save_manifest(self.project, manifest)
        with self.assertRaises(forge_video.WorkflowError) as stale_edge:
            forge_video.approve_artifact(self.project, "direction-wonder", True)
        self.assertIn("Dependency edge is stale", str(stale_edge.exception))
        self.assertNotIn(
            "Dependency Approval is missing or not current", str(stale_edge.exception)
        )

        # Same Revision, new content independently invalidates its hash binding.
        manifest = forge_video.load_manifest(self.project)
        brief = forge_video.find_artifact(manifest, "creative-brief")
        brief["currentRevision"] = original_revision
        brief_path = self.project / brief["path"]
        brief_path.write_text(brief_path.read_text(encoding="utf-8") + "Changed\n", encoding="utf-8")
        brief["contentHash"] = hashlib.sha256(brief_path.read_bytes()).hexdigest()
        forge_video.save_manifest(self.project, manifest)
        with self.assertRaises(forge_video.WorkflowError) as noncurrent_approval:
            forge_video.approve_artifact(self.project, "direction-wonder", True)
        self.assertIn(
            "Dependency Approval is missing or not current",
            str(noncurrent_approval.exception),
        )
        self.assertNotIn("Dependency edge is stale", str(noncurrent_approval.exception))
        self.assertEqual(
            forge_video.load_manifest(self.project)["milestones"]["creativeDirection"],
            "awaiting-approval",
        )

    def test_creative_directions_require_a_creative_brief_approval(self) -> None:
        manifest = forge_video.load_manifest(self.project)
        manifest["approvals"] = [
            approval for approval in manifest["approvals"]
            if approval["artifactId"] != "creative-brief"
        ]
        forge_video.save_manifest(self.project, manifest)

        with self.assertRaisesRegex(
            forge_video.WorkflowError, "current Creative Brief Approval"
        ):
            forge_video.create_creative_directions(self.project, self.directions())

    def test_creative_directions_require_the_brief_approval_to_be_current(self) -> None:
        manifest = forge_video.load_manifest(self.project)
        brief = forge_video.find_artifact(manifest, "creative-brief")
        original_revision = brief["currentRevision"]
        brief["currentRevision"] = original_revision + 1
        forge_video.save_manifest(self.project, manifest)

        with self.assertRaisesRegex(
            forge_video.WorkflowError, "current Creative Brief Approval"
        ):
            forge_video.create_creative_directions(self.project, self.directions())

        manifest = forge_video.load_manifest(self.project)
        brief = forge_video.find_artifact(manifest, "creative-brief")
        brief["currentRevision"] = original_revision
        brief_path = self.project / brief["path"]
        brief_path.write_text(
            brief_path.read_text(encoding="utf-8") + "Creator changed this Revision.\n",
            encoding="utf-8",
        )
        brief["contentHash"] = hashlib.sha256(brief_path.read_bytes()).hexdigest()
        forge_video.save_manifest(self.project, manifest)

        with self.assertRaisesRegex(
            forge_video.WorkflowError, "current Creative Brief Approval"
        ):
            forge_video.create_creative_directions(self.project, self.directions())

    def test_shot_sequence_approval_binds_identity_revision_hash_and_time(self) -> None:
        direction = self.select_and_approve_direction()["approval"]
        result = forge_video.create_shot_sequence(
            self.project, self.shots(), self.reference_bible(), required_story_beat_count=3
        )
        self.assertEqual(
            result["artifact"]["dependencies"],
            [{"artifactId": "direction-wonder", "revision": direction["revision"]}],
        )
        approval_result = forge_video.approve_artifact(self.project, "shot-sequence", True)
        self.assertEqual(approval_result["phase"], "visual-board")
        self.assertEqual(
            forge_video.load_manifest(self.project)["milestones"]["shotSequence"], "approved"
        )
        self.assert_approval_binding("shot-sequence", approval_result["approval"])

    def test_shot_sequence_records_direction_revision_two_dependency_literally(self) -> None:
        self.select_direction_at_revision_two()
        forge_video.approve_artifact(self.project, "direction-wonder", True)
        artifact = forge_video.create_shot_sequence(
            self.project, self.shots(), self.reference_bible(), required_story_beat_count=3
        )["artifact"]
        self.assertEqual(
            artifact["dependencies"],
            [{"artifactId": "direction-wonder", "revision": 2}],
        )

    def test_shot_sequence_approval_records_revision_two_literally(self) -> None:
        self.select_and_approve_direction()
        forge_video.create_shot_sequence(
            self.project, self.shots(), self.reference_bible(), required_story_beat_count=3
        )
        forge_video.create_shot_sequence(
            self.project, self.shots(), self.reference_bible(), required_story_beat_count=3
        )
        approval = forge_video.approve_artifact(
            self.project, "shot-sequence", True
        )["approval"]
        self.assertEqual(approval["revision"], 2)

    def test_shot_sequence_dependency_gate_meta_test_rejects_stale_direction_approval(self) -> None:
        self.select_and_approve_direction()
        forge_video.create_shot_sequence(
            self.project, self.shots(), self.reference_bible(), required_story_beat_count=3
        )
        manifest = forge_video.load_manifest(self.project)
        direction = forge_video.find_artifact(manifest, "direction-wonder")
        original_revision = direction["currentRevision"]

        # Same content, new Revision invalidates the depended-on Approval.
        direction["currentRevision"] = original_revision + 1
        forge_video.save_manifest(self.project, manifest)
        with self.assertRaises(forge_video.WorkflowError) as stale_edge:
            forge_video.approve_artifact(self.project, "shot-sequence", True)
        self.assertIn("Dependency edge is stale", str(stale_edge.exception))
        self.assertNotIn(
            "Dependency Approval is missing or not current", str(stale_edge.exception)
        )

        # Same Revision, new content independently invalidates its hash binding.
        manifest = forge_video.load_manifest(self.project)
        direction = forge_video.find_artifact(manifest, "direction-wonder")
        direction["currentRevision"] = original_revision
        direction_path = self.project / direction["path"]
        direction_path.write_text(
            direction_path.read_text(encoding="utf-8") + "Changed\n", encoding="utf-8"
        )
        direction["contentHash"] = hashlib.sha256(direction_path.read_bytes()).hexdigest()
        forge_video.save_manifest(self.project, manifest)
        with self.assertRaises(forge_video.WorkflowError) as noncurrent_approval:
            forge_video.approve_artifact(self.project, "shot-sequence", True)
        self.assertIn(
            "Dependency Approval is missing or not current",
            str(noncurrent_approval.exception),
        )
        self.assertNotIn("Dependency edge is stale", str(noncurrent_approval.exception))
        self.assertEqual(
            forge_video.load_manifest(self.project)["milestones"]["shotSequence"],
            "awaiting-approval",
        )


if __name__ == "__main__":
    unittest.main()
