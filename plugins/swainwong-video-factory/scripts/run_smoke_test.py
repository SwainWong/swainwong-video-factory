#!/usr/bin/env python3
"""Prepare a fresh topic workflow through research dispatch, without fabricating production work."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Any


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_SCRIPTS = PLUGIN_ROOT / "skills" / "swainwong-video-workflow" / "scripts"
sys.path.insert(0, str(WORKFLOW_SCRIPTS))

import workflow_state  # noqa: E402


NOT_YET_EXERCISED = [
    "research_evidence",
    "script",
    "storyboard",
    "g1_independent_reviews",
    "voice_and_listening",
    "rights_tracked_assets",
    "animation_and_sound_design",
    "editing_first_full_cut",
    "g2_independent_reviews",
    "final_edit",
    "rendered_video",
    "continuous_normal_speed_av_review",
    "g3_independent_reviews",
    "human_acceptance",
    "feedback_to_harness_promotion",
]


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _validate_plugin_layout() -> None:
    for relative in (
        "plugin.json",
        "mcp.json",
        "AGENTS.md",
        "skills/swainwong-video-workflow/SKILL.md",
        "server/workflow_mcp.py",
    ):
        path = PLUGIN_ROOT / relative
        if not path.is_file():
            raise ValueError(f"plugin file missing: {path}")
    public_skills = list((PLUGIN_ROOT / "skills").glob("*/SKILL.md"))
    if len(public_skills) != 1 or public_skills[0].parent.name != "swainwong-video-workflow":
        raise ValueError("plugin must expose exactly one public skill: swainwong-video-workflow")


def run(project: Path, brief: dict[str, Any]) -> dict[str, Any]:
    """Initialize a fresh project and emit only a real research dispatch packet."""
    project = Path(project).resolve()
    _validate_plugin_layout()
    state = workflow_state.initialize_project(project, brief)
    packet = workflow_state.build_task_packet(project, "01-research")
    if not packet["dispatchable"] or packet["stage"] != "research":
        raise ValueError("research task packet is not dispatchable from the locked brief")

    state_dir = project / workflow_state.STATE_DIR
    packet_path = state_dir / "research-task-packet.json"
    _write_json(packet_path, packet)
    report = {
        "schema_version": 1,
        "status": "READY_FOR_RESEARCH",
        "meaning": "The plugin, brief lock, state engine, and research dispatch are wired. No production or review result is implied.",
        "project": str(project),
        "brief_id": brief["brief_id"],
        "brief_revision": brief["revision"],
        "brief_sha256": state["brief"]["config_sha256"],
        "topic": brief["topic"],
        "completed_gates": ["plugin_layout", "brief_lock", "research_dispatch"],
        "task_packet_file": str(packet_path),
        "task_packet": packet,
        "not_yet_exercised": NOT_YET_EXERCISED,
    }
    _write_json(state_dir / "smoke-report.json", report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True, help="Fresh output directory; existing workflow state is rejected.")
    parser.add_argument("--brief", type=Path, required=True, help="Complete, explicitly confirmed production brief JSON.")
    args = parser.parse_args()
    brief = json.loads(args.brief.read_text(encoding="utf-8"))
    print(json.dumps(run(args.project, brief), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
