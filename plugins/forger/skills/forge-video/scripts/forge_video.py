#!/usr/bin/env python3
"""Create and advance a Forger Project through Shot Sequence approval."""
from __future__ import annotations

import argparse, hashlib, json, re, unicodedata, uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INTAKE_FIELDS = ("idea", "purpose", "audience", "channel", "duration", "aspectRatio", "language", "requiredContent", "references", "constraints")
RESEARCH_FIELDS = ("claims", "evidence", "inspiration", "materialContradictions")
CONTRADICTION_RESOLUTION_STATES = ("not-applicable", "unresolved", "resolved")
CREATIVE_BRIEF_ARTIFACT_ID = "creative-brief"
CREATIVE_DIRECTION_MILESTONE = "creativeDirection"
SHOT_SEQUENCE_MILESTONE = "shotSequence"
SHOT_DURATION_TOLERANCE_SECONDS = 0.05
MINIMUM_SHOT_DURATION_SECONDS = 1.0
MINIMUM_BRIEF_DURATION_SECONDS = 5.0
MAXIMUM_BRIEF_DURATION_SECONDS = 180.0
REQUIRED_SHOT_PROPERTIES = (
    "id", "durationSeconds", "purpose", "composition", "framing", "cameraMotion",
    "subjectAction", "lighting", "continuity", "transition", "audio", "dialogue",
    "captions", "editNotes", "visualBoardReferences", "referenceBibleEntityIds",
)
NONEMPTY_SHOT_PROPERTIES = (
    "purpose",
    "composition",
    "framing",
    "cameraMotion",
    "subjectAction",
    "lighting",
    "continuity",
    "transition",
    "audio",
)
SHOT_MARKDOWN_FIELDS = (
    ("id", "ID"),
    ("durationSeconds", "Duration seconds"),
    ("purpose", "Purpose"),
    ("composition", "Composition"),
    ("framing", "Framing"),
    ("cameraMotion", "Camera motion"),
    ("subjectAction", "Subject action"),
    ("lighting", "Lighting"),
    ("continuity", "Continuity"),
    ("transition", "Transition"),
    ("audio", "Audio"),
    ("dialogue", "Dialogue"),
    ("captions", "Captions"),
    ("editNotes", "Edit notes"),
    ("visualBoardReferences", "Visual Board references"),
    ("referenceBibleEntityIds", "Reference Bible entity IDs"),
)

class WorkflowError(ValueError): pass

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "untitled-video"

def reserve_project(root: Path, slug: str) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    suffix = 1
    while True:
        candidate = root / (slug if suffix == 1 else f"{slug}-{suffix}")
        try:
            candidate.mkdir()
            return candidate
        except FileExistsError:
            suffix += 1

def manifest_path(project: Path) -> Path: return project / "forger.project.json"

def load_manifest(project: Path) -> dict[str, Any]:
    try:
        return json.loads(manifest_path(project).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise WorkflowError(f"not a valid Forger Project: {project}") from exc

def save_manifest(project: Path, manifest: dict[str, Any]) -> None:
    manifest["updatedAt"] = utc_now()
    manifest_path(project).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

def content_hash(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()

def create_project(workspace: Path, name: str) -> dict[str, str]:
    project = reserve_project(workspace / "forger-projects", slugify(name))
    project_id, now = str(uuid.uuid4()), utc_now()
    save_manifest(project, {
        "schemaVersion": "0.0.0-dev", "project": {"id": project_id, "name": name, "slug": project.name, "createdAt": now},
        "phase": "intake", "intake": {"answers": {}, "rounds": []}, "artifacts": [], "approvals": [],
        "milestones": {
            "creativeBrief": "pending",
            CREATIVE_DIRECTION_MILESTONE: "pending",
            SHOT_SEQUENCE_MILESTONE: "pending",
        }, "updatedAt": now,
    })
    return {"projectPath": str(project), "projectId": project_id, "phase": "intake"}

def record_intake_round(project: Path, answers: dict[str, Any]) -> dict[str, Any]:
    if not 1 <= len(answers) <= 3: raise WorkflowError("an intake round must answer between one and three related questions")
    unknown = sorted(set(answers) - set(INTAKE_FIELDS))
    if unknown: raise WorkflowError("unknown intake fields: " + ", ".join(unknown))
    empty = sorted(k for k, v in answers.items() if v is None or v == "")
    if empty: raise WorkflowError("intake answers cannot be empty: " + ", ".join(empty))
    if "duration" in answers:
        duration_seconds = parse_duration_seconds(answers["duration"])
        if not MINIMUM_BRIEF_DURATION_SECONDS <= duration_seconds <= MAXIMUM_BRIEF_DURATION_SECONDS:
            raise WorkflowError(
                "Creative Brief duration must be between 5 seconds and 3 minutes"
            )
    manifest = load_manifest(project); intake = manifest["intake"]
    repeated = sorted(set(answers) & set(intake["answers"]))
    if repeated: raise WorkflowError("intake fields already known: " + ", ".join(repeated))
    intake["answers"].update(answers); intake["rounds"].append({"fields": list(answers), "answeredAt": utc_now()})
    missing = [field for field in INTAKE_FIELDS if field not in intake["answers"]]
    manifest["phase"] = "brief-ready" if not missing else "intake"; save_manifest(project, manifest)
    return {"phase": manifest["phase"], "missingFields": missing}

def empty_research(disposition: str) -> dict[str, Any]:
    return {"disposition": disposition, "claims": [], "evidence": [], "inspiration": [], "materialContradictions": [],
            "contradictionResolutionState": "not-applicable" if disposition == "not-warranted" else "unresolved"}

def validate_research(research: dict[str, Any]) -> None:
    required = {"disposition", *RESEARCH_FIELDS, "contradictionResolutionState"}; missing = sorted(required - set(research))
    if missing: raise WorkflowError("research is missing fields: " + ", ".join(missing))
    if research["disposition"] not in ("not-warranted", "warranted"): raise WorkflowError("invalid research disposition")
    if research["contradictionResolutionState"] not in CONTRADICTION_RESOLUTION_STATES:
        raise WorkflowError("invalid contradiction resolution state")
    for field in RESEARCH_FIELDS:
        if not isinstance(research[field], list): raise WorkflowError(f"research {field} must be a list")
    for claim in research["claims"]:
        if not isinstance(claim, dict) or not claim.get("citationReferences"):
            raise WorkflowError("every Research Claim must include citationReferences")

def render_creative_brief(answers: dict[str, Any], research: dict[str, Any]) -> str:
    lines = ["# Creative Brief", "", "## Intent", "", f"- Idea: {answers['idea']}", f"- Purpose: {answers['purpose']}",
             f"- Audience: {answers['audience']}", "", "## Delivery", "", f"- Channel: {answers['channel']}",
             f"- Duration: {answers['duration']}", f"- Aspect ratio: {answers['aspectRatio']}", f"- Language: {answers['language']}",
             "", "## Requirements", "", f"- Required content: {answers['requiredContent']}", f"- References: {answers['references']}",
             f"- Constraints: {answers['constraints']}", "", "## Research", "", f"- Disposition: {research['disposition']}",
             f"- Contradiction resolution state: {research['contradictionResolutionState']}"]
    for heading, key in (("Research Claims", "claims"), ("Evidence", "evidence"), ("Inspiration", "inspiration"), ("Material Contradictions", "materialContradictions")):
        lines += ["", f"### {heading}", ""]
        lines += [f"- {json.dumps(v, ensure_ascii=False, sort_keys=True)}" for v in research[key]] or ["None."]
    return "\n".join(lines) + "\n"

def create_creative_brief(project: Path, research: dict[str, Any]) -> dict[str, Any]:
    validate_research(research); manifest = load_manifest(project)
    missing = [f for f in INTAKE_FIELDS if f not in manifest["intake"]["answers"]]
    if missing: raise WorkflowError("required intake is missing: " + ", ".join(missing))
    if research["disposition"] == "warranted" and not research["claims"]: raise WorkflowError("warranted research requires a Research Claim")
    artifact_dir = project / "artifacts"; artifact_dir.mkdir(exist_ok=True); path = artifact_dir / "creative-brief.md"
    path.write_text(render_creative_brief(manifest["intake"]["answers"], research), encoding="utf-8")
    previous = next((a for a in manifest["artifacts"] if a["id"] == CREATIVE_BRIEF_ARTIFACT_ID), None)
    artifact = {"id": CREATIVE_BRIEF_ARTIFACT_ID, "type": "creative-brief", "path": str(path.relative_to(project)),
                "currentRevision": 1 if previous is None else previous["currentRevision"] + 1,
                "contentHash": content_hash(path), "revisionState": "current", "research": research,
                "dependencies": [],
                "approvalBlockers": (["Material Contradictions are unresolved"]
                    if research["materialContradictions"] and research["contradictionResolutionState"] != "resolved" else []),
                "workflow": {"milestone": "creativeBrief", "phaseOnApproval": "creative-direction"}}
    manifest["artifacts"] = [a for a in manifest["artifacts"] if a["id"] != artifact["id"]] + [artifact]
    manifest["phase"] = "creative-brief-review"; manifest["milestones"]["creativeBrief"] = "awaiting-approval"; save_manifest(project, manifest)
    return {"phase": manifest["phase"], "artifact": artifact}

def find_artifact(manifest: dict[str, Any], artifact_id: str) -> dict[str, Any]:
    try: return next(a for a in manifest["artifacts"] if a["id"] == artifact_id)
    except StopIteration as exc: raise WorkflowError(f"unknown Artifact: {artifact_id}") from exc

def render_creative_direction(direction: dict[str, Any]) -> str:
    return (
        f"# {direction['title']}\n\n"
        f"## Narrative axis\n\n{direction['narrativeAxis']}\n\n"
        f"## Aesthetic axis\n\n{direction['aestheticAxis']}\n"
    )

def validate_creative_directions(directions: list[dict[str, Any]]) -> None:
    if not isinstance(directions, list):
        raise WorkflowError("Creative Directions must be a list")
    if len(directions) != 3:
        raise WorkflowError("exactly three Creative Directions are required")
    required = {"id", "title", "recommended", "narrativeAxis", "aestheticAxis"}
    if any(not isinstance(direction, dict) or required - set(direction) for direction in directions):
        raise WorkflowError("every Creative Direction requires identity, title, recommendation, and narrative and aesthetic axes")
    if len({direction["id"] for direction in directions}) != 3:
        raise WorkflowError("Creative Direction identities must be unique")
    if any(
        not isinstance(direction[field], str) or not direction[field].strip()
        for direction in directions for field in ("id", "title")
    ):
        raise WorkflowError("Creative Direction identity and title must be non-empty")
    if any(not isinstance(direction["recommended"], bool) for direction in directions):
        raise WorkflowError("Creative Direction recommended marks must be boolean")
    if sum(direction["recommended"] is True for direction in directions) != 1:
        raise WorkflowError("exactly one Creative Direction must be recommended")
    if any(
        not isinstance(direction[axis], str) or not direction[axis].strip()
        for direction in directions for axis in ("narrativeAxis", "aestheticAxis")
    ):
        raise WorkflowError("Creative Direction narrative and aesthetic axes must be non-empty")
    axes = {
        (direction["narrativeAxis"].strip(), direction["aestheticAxis"].strip())
        for direction in directions
    }
    if len(axes) != 3:
        raise WorkflowError("Creative Direction narrative and aesthetic axes must not be identical")

def create_creative_directions(project: Path, directions: list[dict[str, Any]]) -> dict[str, Any]:
    validate_creative_directions(directions)
    manifest = load_manifest(project)
    brief = find_artifact(manifest, CREATIVE_BRIEF_ARTIFACT_ID)
    brief_approval = next(
        (
            approval for approval in manifest["approvals"]
            if approval["artifactId"] == brief["id"]
        ),
        None,
    )
    if brief_approval is None or not approval_is_current(project, brief_approval):
        raise WorkflowError("Creative Directions require a current Creative Brief Approval")
    prior = {
        artifact["id"]: artifact for artifact in manifest["artifacts"]
        if artifact.get("type") == "creative-direction"
    }
    artifact_dir = project / "artifacts" / "creative-directions"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    records = []
    for supplied in directions:
        direction = dict(supplied)
        old = prior.get(direction["id"])
        path = artifact_dir / f"{slugify(direction['id'])}.md"
        path.write_text(render_creative_direction(direction), encoding="utf-8")
        direction.update({
            "type": "creative-direction",
            "path": str(path.relative_to(project)),
            "currentRevision": 1 if old is None else old["currentRevision"] + 1,
            "contentHash": content_hash(path),
            "revisionState": "current",
            "dependencies": [{"artifactId": brief["id"], "revision": brief["currentRevision"]}],
            "approvalBlockers": (
                [] if old and old.get("selectionState") == "selected"
                and manifest.get("selectedCreativeDirectionId") == direction["id"]
                else ["Creative Direction is not selected"]
            ),
            "workflow": {"milestone": CREATIVE_DIRECTION_MILESTONE, "phaseOnApproval": "shot-sequence"},
            "selectionState": "proposed" if old is None else old.get("selectionState", "proposed"),
            "rejectionHistory": [] if old is None else old.get("rejectionHistory", []),
        })
        records.append(direction)
    manifest["artifacts"] = [
        artifact for artifact in manifest["artifacts"]
        if artifact.get("type") != "creative-direction"
    ] + records
    manifest.pop("creativeDirections", None)
    manifest["phase"] = "creative-direction-review"
    if manifest.get("selectedCreativeDirectionId") not in {direction["id"] for direction in records}:
        manifest.pop("selectedCreativeDirectionId", None)
        manifest["milestones"][CREATIVE_DIRECTION_MILESTONE] = "awaiting-selection"
    else:
        manifest["milestones"][CREATIVE_DIRECTION_MILESTONE] = "awaiting-approval"
    save_manifest(project, manifest)
    return {"phase": manifest["phase"], "directions": records}

def select_creative_direction(project: Path, selected_id: str, rejection_reasons: dict[str, str]) -> dict[str, Any]:
    manifest = load_manifest(project)
    directions = [
        artifact for artifact in manifest["artifacts"]
        if artifact.get("type") == "creative-direction"
    ]
    manifest.pop("creativeDirections", None)
    previously_selected_id = manifest.get("selectedCreativeDirectionId")
    selected = next((direction for direction in directions if direction["id"] == selected_id), None)
    if selected is None:
        raise WorkflowError(f"unknown Creative Direction: {selected_id}")
    rejected_ids = {direction["id"] for direction in directions if direction["id"] != selected_id}
    if set(rejection_reasons) != rejected_ids or any(
        not isinstance(reason, str) or not reason.strip() for reason in rejection_reasons.values()
    ):
        raise WorkflowError("selection requires a Creator-supplied rejection reason for every rejected Creative Direction")
    now = utc_now()
    for direction in directions:
        if direction["id"] == selected_id:
            direction["selectionState"] = "selected"
            direction["selectedAt"] = now
        else:
            direction["selectionState"] = "rejected"
            direction.setdefault("rejectionHistory", []).append({
                "reason": rejection_reasons[direction["id"]], "rejectedAt": now
            })
        direction["approvalBlockers"] = (
            [] if direction["id"] == selected_id else ["Creative Direction is not selected"]
        )
    if previously_selected_id is not None and previously_selected_id != selected_id:
        manifest["approvals"] = [
            approval for approval in manifest["approvals"]
            if approval["artifactId"] != previously_selected_id
        ]
    manifest["selectedCreativeDirectionId"] = selected_id
    manifest["milestones"][CREATIVE_DIRECTION_MILESTONE] = "awaiting-approval"
    manifest["phase"] = "creative-direction-review"
    save_manifest(project, manifest)
    return {"phase": manifest["phase"], "selectedCreativeDirectionId": selected_id}

def parse_duration_seconds(value: Any) -> float:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        duration = float(value)
    elif isinstance(value, str):
        text = value.strip()
        combined = re.fullmatch(
            r"(\d+(?:\.\d+)?)\s*m(?:in(?:ute)?s?)?\s*"
            r"(\d+(?:\.\d+)?)\s*s(?:ec(?:ond)?s?)?",
            text,
            re.IGNORECASE,
        )
        clock = re.fullmatch(r"(\d+):(\d{1,2}(?:\.\d+)?)", text)
        minutes = re.fullmatch(
            r"(\d+(?:\.\d+)?)\s*(?:minutes?|mins?|m)", text, re.IGNORECASE
        )
        seconds = re.fullmatch(
            r"(\d+(?:\.\d+)?)\s*(?:seconds?|s)?", text, re.IGNORECASE
        )
        if combined:
            duration = float(combined.group(1)) * 60 + float(combined.group(2))
        elif clock and float(clock.group(2)) < 60:
            duration = float(clock.group(1)) * 60 + float(clock.group(2))
        elif minutes:
            duration = float(minutes.group(1)) * 60
        elif seconds:
            duration = float(seconds.group(1))
        else:
            raise WorkflowError(
                "Creative Brief duration must be expressed in seconds or minutes"
            )
    else:
        raise WorkflowError("Creative Brief duration must be expressed in seconds or minutes")
    if duration <= 0:
        raise WorkflowError("Creative Brief duration must be positive")
    return duration

def validate_reference_bible(entities: list[dict[str, Any]]) -> set[str]:
    if not isinstance(entities, list):
        raise WorkflowError("Reference Bible entities must be a list")
    ids: list[str] = []
    for entity in entities:
        if not isinstance(entity, dict) or any(not entity.get(field) for field in ("id", "type", "name")):
            raise WorkflowError("every Reference Bible entity requires id, type, and name")
        ids.append(entity["id"])
    if len(ids) != len(set(ids)):
        raise WorkflowError("Reference Bible entity identities must be unique")
    return set(ids)

def validate_shots(shots: list[dict[str, Any]], reference_entity_ids: set[str]) -> None:
    if not isinstance(shots, list) or not shots:
        raise WorkflowError("Shot Sequence requires at least one Shot")
    for index, shot in enumerate(shots, start=1):
        if not isinstance(shot, dict):
            raise WorkflowError(f"Shot {index} must be an object")
        missing = [field for field in REQUIRED_SHOT_PROPERTIES if field not in shot]
        if missing:
            raise WorkflowError(f"Shot {index} is missing required properties: " + ", ".join(missing))
        empty = [
            field for field in NONEMPTY_SHOT_PROPERTIES
            if not isinstance(shot[field], str) or not shot[field].strip()
        ]
        if empty:
            raise WorkflowError(
                f"Shot {index} requires non-empty values for: " + ", ".join(empty)
            )
        if not isinstance(shot["durationSeconds"], (int, float)) or isinstance(shot["durationSeconds"], bool):
            raise WorkflowError(f"Shot {index} durationSeconds must be numeric")
        if not isinstance(shot["referenceBibleEntityIds"], list):
            raise WorkflowError(f"Shot {index} referenceBibleEntityIds must be a list")
        unknown = sorted(set(shot["referenceBibleEntityIds"]) - reference_entity_ids)
        if unknown:
            raise WorkflowError(
                f"Shot {index} references unknown Reference Bible entity: " + ", ".join(unknown)
            )
    ids = [shot["id"] for shot in shots]
    if len(ids) != len(set(ids)):
        raise WorkflowError("Shot identities must be unique")

def timing_blockers(
    shots: list[dict[str, Any]], brief_duration_seconds: float, required_story_beat_count: int
) -> list[str]:
    if not isinstance(required_story_beat_count, int) or isinstance(required_story_beat_count, bool) or required_story_beat_count < 1:
        raise WorkflowError("required story-beat count must be a positive integer")
    blockers = []
    total = sum(float(shot["durationSeconds"]) for shot in shots)
    if abs(total - brief_duration_seconds) > SHOT_DURATION_TOLERANCE_SECONDS:
        blockers.append(
            f"Shot durations total {total:g} seconds and must equal the approved Creative Brief duration "
            f"of {brief_duration_seconds:g} seconds within {SHOT_DURATION_TOLERANCE_SECONDS:g} seconds; "
            f"adjust the Shot durations by {brief_duration_seconds - total:+g} seconds"
        )
    short = [shot["id"] for shot in shots if float(shot["durationSeconds"]) < MINIMUM_SHOT_DURATION_SECONDS]
    if short:
        blockers.append(
            f"Shots must be at least {MINIMUM_SHOT_DURATION_SECONDS:g} second; lengthen or merge: "
            + ", ".join(short)
        )
    minimum_beat_total = required_story_beat_count * MINIMUM_SHOT_DURATION_SECONDS
    if minimum_beat_total > brief_duration_seconds:
        maximum_beats = int(brief_duration_seconds // MINIMUM_SHOT_DURATION_SECONDS)
        blockers.append(
            f"{required_story_beat_count} required story beats need at least {minimum_beat_total:g} seconds; "
            f"reduce to at most {maximum_beats} story beats or increase the approved Creative Brief duration"
        )
    return blockers

def render_shot_sequence(
    shots: list[dict[str, Any]], reference_bible: list[dict[str, Any]], timing: dict[str, Any]
) -> str:
    lines = ["# Shot Sequence", "", "## Timing", "", f"- Approved brief duration: {timing['briefDurationSeconds']:g} seconds",
             f"- Shot duration total: {timing['shotDurationTotalSeconds']:g} seconds",
             f"- Required story beats: {timing['requiredStoryBeatCount']}", "", "## Reference Bible", ""]
    lines += [f"- `{entity['id']}` ({entity['type']}): {entity['name']}" for entity in reference_bible] or ["None."]
    lines += ["", "## Shots", ""]
    for shot in shots:
        lines += [f"### {shot['id']}", ""]
        for field, label in SHOT_MARKDOWN_FIELDS:
            value = shot[field]
            if value == "" or value == []:
                rendered_value = "None."
            elif isinstance(value, list):
                rendered_value = ", ".join(str(item) for item in value)
            elif isinstance(value, (int, float)) and not isinstance(value, bool):
                rendered_value = f"{value:g}"
            else:
                rendered_value = str(value)
            lines.append(f"- {label}: {rendered_value}")
        lines.append("")
    return "\n".join(lines)

def create_shot_sequence(
    project: Path,
    shots: list[dict[str, Any]],
    reference_bible: list[dict[str, Any]],
    required_story_beat_count: int,
) -> dict[str, Any]:
    reference_entity_ids = validate_reference_bible(reference_bible)
    validate_shots(shots, reference_entity_ids)
    manifest = load_manifest(project)
    selected_id = manifest.get("selectedCreativeDirectionId")
    if not selected_id:
        raise WorkflowError("Shot Sequence requires an explicitly selected Creative Direction")
    selected = find_artifact(manifest, selected_id)
    brief = find_artifact(manifest, CREATIVE_BRIEF_ARTIFACT_ID)
    brief_approval = next(
        (approval for approval in manifest["approvals"] if approval["artifactId"] == brief["id"]), None
    )
    if brief_approval is None or not approval_is_current(project, brief_approval):
        raise WorkflowError("Shot Sequence timing requires a current Creative Brief Approval")
    brief_duration = parse_duration_seconds(manifest["intake"]["answers"]["duration"])
    blockers = timing_blockers(shots, brief_duration, required_story_beat_count)
    if blockers:
        manifest["milestones"][SHOT_SEQUENCE_MILESTONE] = "paused"
        save_manifest(project, manifest)
        raise WorkflowError("Shot Sequence timing is infeasible: " + "; ".join(blockers))
    timing = {
        "briefDurationSeconds": brief_duration,
        "shotDurationTotalSeconds": sum(float(shot["durationSeconds"]) for shot in shots),
        "toleranceSeconds": SHOT_DURATION_TOLERANCE_SECONDS,
        "minimumShotDurationSeconds": MINIMUM_SHOT_DURATION_SECONDS,
        "requiredStoryBeatCount": required_story_beat_count,
    }
    artifact_dir = project / "artifacts"
    artifact_dir.mkdir(exist_ok=True)
    path = artifact_dir / "shot-sequence.md"
    path.write_text(render_shot_sequence(shots, reference_bible, timing), encoding="utf-8")
    old = next((artifact for artifact in manifest["artifacts"] if artifact["id"] == "shot-sequence"), None)
    artifact = {
        "id": "shot-sequence", "type": "shot-sequence", "path": str(path.relative_to(project)),
        "currentRevision": 1 if old is None else old["currentRevision"] + 1,
        "contentHash": content_hash(path), "revisionState": "current",
        "dependencies": [{"artifactId": selected["id"], "revision": selected["currentRevision"]}],
        "approvalBlockers": [],
        "workflow": {"milestone": SHOT_SEQUENCE_MILESTONE, "phaseOnApproval": "visual-board"},
        "shots": shots, "referenceBible": reference_bible, "timing": timing,
    }
    manifest["artifacts"] = [
        candidate for candidate in manifest["artifacts"] if candidate["id"] != artifact["id"]
    ] + [artifact]
    manifest["milestones"][SHOT_SEQUENCE_MILESTONE] = "awaiting-approval"
    manifest["phase"] = "shot-sequence-review"
    save_manifest(project, manifest)
    return {"phase": manifest["phase"], "artifact": artifact, "timing": timing}

def approval_is_current(project: Path, approval: dict[str, Any]) -> bool:
    manifest = load_manifest(project)
    try:
        artifact = find_artifact(manifest, approval["artifactId"]); actual = content_hash(project / artifact["path"])
    except (WorkflowError, FileNotFoundError): return False
    return approval.get("revision") == artifact.get("currentRevision") and approval.get("contentHash") == artifact.get("contentHash") == actual

def approval_blockers(project: Path, artifact_id: str, supplied: list[str] | None = None) -> list[str]:
    manifest = load_manifest(project); artifact = find_artifact(manifest, artifact_id); blockers = list(supplied or []); path = project / artifact["path"]
    if not path.is_file(): blockers.append("Artifact content is missing")
    elif content_hash(path) != artifact["contentHash"]: blockers.append("Artifact content changed after the current Revision was recorded")
    blockers.extend(artifact.get("approvalBlockers", []))
    for dependency in artifact.get("dependencies", []):
        approval = next(
            (candidate for candidate in manifest["approvals"] if candidate["artifactId"] == dependency["artifactId"]),
            None,
        )
        if (
            approval is None
            or approval.get("revision") != dependency.get("revision")
            or not approval_is_current(project, approval)
        ):
            blockers.append(
                f"Dependency Approval is not current: {dependency['artifactId']} Revision {dependency['revision']}"
            )
    return blockers

def approve_artifact(project: Path, artifact_id: str, creator_approved: bool, supplied_blockers: list[str] | None = None) -> dict[str, Any]:
    if not creator_approved: raise WorkflowError("explicit Creator Approval is required")
    blockers = approval_blockers(project, artifact_id, supplied_blockers)
    if blockers: raise WorkflowError("approval blocked: " + "; ".join(blockers))
    manifest = load_manifest(project); artifact = find_artifact(manifest, artifact_id)
    approval = {"artifactId": artifact["id"], "revision": artifact["currentRevision"], "contentHash": artifact["contentHash"], "approvedAt": utc_now()}
    manifest["approvals"] = [a for a in manifest["approvals"] if a["artifactId"] != artifact_id] + [approval]
    workflow = artifact.get("workflow")
    if not workflow:
        raise WorkflowError(f"Artifact has no declared approval workflow: {artifact_id}")
    manifest["milestones"][workflow["milestone"]] = "approved"
    manifest["phase"] = workflow["phaseOnApproval"]
    save_manifest(project, manifest); return {"phase": manifest["phase"], "approval": approval, "current": True}

def project_status(project: Path) -> dict[str, Any]:
    manifest = load_manifest(project)
    return {"phase": manifest["phase"], "approvals": [{**a, "current": approval_is_current(project, a)} for a in manifest["approvals"]]}

def json_object(value: str) -> dict[str, Any]:
    value = json.loads(value)
    if not isinstance(value, dict): raise argparse.ArgumentTypeError("value must be a JSON object")
    return value

def json_array(value: str) -> list[Any]:
    value = json.loads(value)
    if not isinstance(value, list): raise argparse.ArgumentTypeError("value must be a JSON array")
    return value

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--workspace", type=Path); parser.add_argument("--name")
    actions = parser.add_subparsers(dest="action")
    intake = actions.add_parser("intake"); intake.add_argument("--project", type=Path, required=True); intake.add_argument("--answers", type=json_object, required=True)
    brief = actions.add_parser("brief"); brief.add_argument("--project", type=Path, required=True); brief.add_argument("--research", type=json_object); brief.add_argument("--research-disposition", choices=("not-warranted", "warranted"))
    directions = actions.add_parser("directions"); directions.add_argument("--project", type=Path, required=True); directions.add_argument("--directions", type=json_array, required=True)
    select_direction = actions.add_parser("select-direction"); select_direction.add_argument("--project", type=Path, required=True); select_direction.add_argument("--selected", required=True); select_direction.add_argument("--rejection-reasons", type=json_object, required=True)
    shots = actions.add_parser("shots"); shots.add_argument("--project", type=Path, required=True); shots.add_argument("--shots", type=json_array, required=True); shots.add_argument("--reference-bible", type=json_array, required=True); shots.add_argument("--required-story-beat-count", type=int, required=True)
    approve = actions.add_parser("approve"); approve.add_argument("--project", type=Path, required=True); approve.add_argument("--artifact", default=CREATIVE_BRIEF_ARTIFACT_ID); approve.add_argument("--creator-approved", action="store_true"); approve.add_argument("--blocker", action="append", default=[])
    status = actions.add_parser("status"); status.add_argument("--project", type=Path, required=True)
    return parser.parse_args()

def main() -> None:
    args = parse_args()
    try:
        if args.action == "intake": result = record_intake_round(args.project.resolve(), args.answers)
        elif args.action == "brief":
            if args.research is None and args.research_disposition is None: raise WorkflowError("brief requires research or a research disposition")
            result = create_creative_brief(args.project.resolve(), args.research or empty_research(args.research_disposition))
        elif args.action == "directions": result = create_creative_directions(args.project.resolve(), args.directions)
        elif args.action == "select-direction": result = select_creative_direction(args.project.resolve(), args.selected, args.rejection_reasons)
        elif args.action == "shots": result = create_shot_sequence(args.project.resolve(), args.shots, args.reference_bible, args.required_story_beat_count)
        elif args.action == "approve": result = approve_artifact(args.project.resolve(), args.artifact, args.creator_approved, args.blocker)
        elif args.action == "status": result = project_status(args.project.resolve())
        else:
            if args.workspace is None or not args.name: raise WorkflowError("project creation requires --workspace and --name")
            result = create_project(args.workspace.resolve(), args.name)
    except WorkflowError as exc: raise SystemExit(str(exc)) from exc
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))

if __name__ == "__main__": main()
