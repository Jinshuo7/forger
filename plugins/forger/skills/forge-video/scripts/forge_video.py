#!/usr/bin/env python3
"""Create the first observable slice of a Forger Project."""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def slugify(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-")
    return slug or "untitled-video"


def reserve_project(projects_root: Path, base_slug: str) -> Path:
    projects_root.mkdir(parents=True, exist_ok=True)
    suffix = 1
    while True:
        slug = base_slug if suffix == 1 else f"{base_slug}-{suffix}"
        candidate = projects_root / slug
        try:
            candidate.mkdir()
            return candidate
        except FileExistsError:
            suffix += 1


class GenerationMonitor:
    """Observe and enforce the generation boundary for this slice."""

    KEYFRAME_EVENT = "keyframe_image.generated"
    FINAL_VIDEO_EVENT = "final_video_job.submitted"

    def __init__(self) -> None:
        self.events: list[dict[str, str]] = []

    def observe(self, event: dict[str, str]) -> None:
        self.events.append(event)

    def assert_none_crossed(self) -> None:
        if self.events:
            names = ", ".join(event.get("event", "unknown") for event in self.events)
            raise AssertionError(f"the walking skeleton crossed a generation boundary: {names}")


def create_project(workspace: Path, name: str) -> dict[str, object]:
    project_path = reserve_project(workspace / "forger-projects", slugify(name))
    project_id = str(uuid.uuid4())
    created_at = utc_now()
    monitor = GenerationMonitor()

    manifest = {
        "schemaVersion": "0.0.0-dev",
        "project": {
            "id": project_id,
            "name": name,
            "slug": project_path.name,
            "createdAt": created_at,
        },
        "phase": "walking-skeleton",
    }
    (project_path / "forger.project.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    monitor.assert_none_crossed()

    return {
        "projectPath": str(project_path),
        "projectId": project_id,
        "phase": "walking-skeleton",
        "generationEvents": monitor.events,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--name", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = create_project(args.workspace.resolve(), args.name)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
