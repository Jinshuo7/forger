#!/usr/bin/env python3
"""Create and advance a Forger Project through Creative Brief approval."""
from __future__ import annotations

import argparse, hashlib, json, re, unicodedata, uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INTAKE_FIELDS = ("idea", "purpose", "audience", "channel", "duration", "aspectRatio", "language", "requiredContent", "references", "constraints")
RESEARCH_FIELDS = ("claims", "evidence", "inspiration", "materialContradictions")
CREATIVE_BRIEF_ARTIFACT_ID = "creative-brief"

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
        "milestones": {"creativeBrief": "pending"}, "updatedAt": now,
    })
    return {"projectPath": str(project), "projectId": project_id, "phase": "intake"}

def record_intake_round(project: Path, answers: dict[str, Any]) -> dict[str, Any]:
    if not 1 <= len(answers) <= 3: raise WorkflowError("an intake round must answer between one and three related questions")
    unknown = sorted(set(answers) - set(INTAKE_FIELDS))
    if unknown: raise WorkflowError("unknown intake fields: " + ", ".join(unknown))
    empty = sorted(k for k, v in answers.items() if v is None or v == "")
    if empty: raise WorkflowError("intake answers cannot be empty: " + ", ".join(empty))
    manifest = load_manifest(project); intake = manifest["intake"]
    repeated = sorted(set(answers) & set(intake["answers"]))
    if repeated: raise WorkflowError("intake fields already known: " + ", ".join(repeated))
    intake["answers"].update(answers); intake["rounds"].append({"fields": list(answers), "answeredAt": utc_now()})
    missing = [field for field in INTAKE_FIELDS if field not in intake["answers"]]
    manifest["phase"] = "brief-ready" if not missing else "intake"; save_manifest(project, manifest)
    return {"phase": manifest["phase"], "missingFields": missing}

def empty_research(disposition: str) -> dict[str, Any]:
    return {"disposition": disposition, "claims": [], "evidence": [], "inspiration": [], "materialContradictions": [],
            "contradictionResolutionState": "not-applicable" if disposition == "not-warranted" else "resolved"}

def validate_research(research: dict[str, Any]) -> None:
    required = {"disposition", *RESEARCH_FIELDS, "contradictionResolutionState"}; missing = sorted(required - set(research))
    if missing: raise WorkflowError("research is missing fields: " + ", ".join(missing))
    if research["disposition"] not in ("not-warranted", "warranted"): raise WorkflowError("invalid research disposition")
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
    artifact = {"id": CREATIVE_BRIEF_ARTIFACT_ID, "type": "creative-brief", "path": str(path.relative_to(project)),
                "currentRevision": 1, "contentHash": content_hash(path), "status": "current", "research": research}
    manifest["artifacts"] = [a for a in manifest["artifacts"] if a["id"] != artifact["id"]] + [artifact]
    manifest["phase"] = "creative-brief-review"; manifest["milestones"]["creativeBrief"] = "awaiting-approval"; save_manifest(project, manifest)
    return {"phase": manifest["phase"], "artifact": artifact}

def find_artifact(manifest: dict[str, Any], artifact_id: str) -> dict[str, Any]:
    try: return next(a for a in manifest["artifacts"] if a["id"] == artifact_id)
    except StopIteration as exc: raise WorkflowError(f"unknown Artifact: {artifact_id}") from exc

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
    research = artifact.get("research", {})
    if research.get("materialContradictions") and research.get("contradictionResolutionState") != "resolved": blockers.append("Material Contradictions are unresolved")
    return blockers

def approve_artifact(project: Path, artifact_id: str, creator_approved: bool, supplied_blockers: list[str] | None = None) -> dict[str, Any]:
    if not creator_approved: raise WorkflowError("explicit Creator Approval is required")
    blockers = approval_blockers(project, artifact_id, supplied_blockers)
    if blockers: raise WorkflowError("approval blocked: " + "; ".join(blockers))
    manifest = load_manifest(project); artifact = find_artifact(manifest, artifact_id)
    approval = {"artifactId": artifact["id"], "revision": artifact["currentRevision"], "contentHash": artifact["contentHash"], "approvedAt": utc_now()}
    manifest["approvals"] = [a for a in manifest["approvals"] if a["artifactId"] != artifact_id] + [approval]; artifact["status"] = "approved"
    if artifact_id == CREATIVE_BRIEF_ARTIFACT_ID:
        manifest["milestones"]["creativeBrief"] = "approved"; manifest["phase"] = "creative-direction"
    save_manifest(project, manifest); return {"phase": manifest["phase"], "approval": approval, "current": True}

def project_status(project: Path) -> dict[str, Any]:
    manifest = load_manifest(project)
    return {"phase": manifest["phase"], "approvals": [{**a, "current": approval_is_current(project, a)} for a in manifest["approvals"]]}

def json_object(value: str) -> dict[str, Any]:
    value = json.loads(value)
    if not isinstance(value, dict): raise argparse.ArgumentTypeError("value must be a JSON object")
    return value

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--workspace", type=Path); parser.add_argument("--name")
    actions = parser.add_subparsers(dest="action")
    intake = actions.add_parser("intake"); intake.add_argument("--project", type=Path, required=True); intake.add_argument("--answers", type=json_object, required=True)
    brief = actions.add_parser("brief"); brief.add_argument("--project", type=Path, required=True); brief.add_argument("--research", type=json_object); brief.add_argument("--research-disposition", choices=("not-warranted", "warranted"))
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
        elif args.action == "approve": result = approve_artifact(args.project.resolve(), args.artifact, args.creator_approved, args.blocker)
        elif args.action == "status": result = project_status(args.project.resolve())
        else:
            if args.workspace is None or not args.name: raise WorkflowError("project creation requires --workspace and --name")
            result = create_project(args.workspace.resolve(), args.name)
    except WorkflowError as exc: raise SystemExit(str(exc)) from exc
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))

if __name__ == "__main__": main()
