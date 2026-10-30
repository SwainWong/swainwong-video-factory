#!/usr/bin/env python3
"""Deterministic, file-backed gates for the SwainWong video workflow."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile


SKILL_ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = ".video-workflow"
ALLOWED_RESULTS = {"READY", "REVISE", "PARTIAL", "UNAVAILABLE", "BLOCKED"}
STORED_RESULTS = ALLOWED_RESULTS | {"NOT_STARTED", "STALE"}

STAGES = {
    "brief": [],
    "research": ["brief"],
    "scriptwriting": ["research"],
    "g1-director-review": ["research", "scriptwriting"],
    "g1-fact-review": ["research", "scriptwriting"],
    "storyboard": ["g1-director-review", "g1-fact-review"],
    "editing-first-full-cut": ["scriptwriting", "storyboard"],
    "g1-visual-review": ["storyboard"],
    "g2-director-review": ["editing-first-full-cut"],
    "g2-visual-review": ["editing-first-full-cut"],
    "g2-fact-review": ["editing-first-full-cut"],
    "voice": ["editing-first-full-cut"],
    "assets": ["editing-first-full-cut"],
    "bgm": ["editing-first-full-cut"],
    "animation": ["voice", "assets"],
    "editing-final": [
        "g1-visual-review",
        "g2-director-review",
        "g2-visual-review",
        "g2-fact-review",
        "voice",
        "assets",
        "animation",
        "bgm",
    ],
    "g3-director-review": ["editing-final"],
    "g3-visual-review": ["editing-final"],
    "g3-fact-review": ["editing-final"],
    "candidate-internal-gate": ["g3-director-review", "g3-visual-review", "g3-fact-review"],
    "owner-review-ready": ["candidate-internal-gate"],
    "delivery": ["owner-review-ready"],
    "feedback": ["owner-review-ready"],
}

ROLE_STAGES = {
    "01-research": ["research"],
    "02-scriptwriting": ["scriptwriting"],
    "03-storyboard": ["storyboard"],
    "04-voice": ["voice"],
    "05-assets": ["assets"],
    "06-animation": ["animation"],
    "07-editing": ["editing-first-full-cut", "editing-final"],
    "08-delivery": ["candidate-internal-gate", "owner-review-ready", "delivery", "feedback"],
    "09-director-review": ["g1-director-review", "g2-director-review", "g3-director-review"],
    "10-visual-review": ["g1-visual-review", "g2-visual-review", "g3-visual-review"],
    "11-fact-review": ["g1-fact-review", "g2-fact-review", "g3-fact-review"],
    "12-bgm": ["bgm"],
}

REQUIRED_BRIEF_PATHS = (
    "brief_id",
    "revision",
    "confirmation_basis",
    "topic",
    "viewpoint",
    "audience",
    "purpose",
    "aspect_ratio",
    "duration.target_seconds",
    "duration.tolerance_before_seconds",
    "duration.tolerance_after_seconds",
    "voice.spoken_language",
    "voice.source",
    "voice.profile_ref",
    "voice.verification_status",
    "subtitles.language",
    "subtitles.render_authority",
    "visual.asset_policy",
    "visual.forbidden_asset_types",
    "platform",
    "delivery.resolution",
    "delivery.scope",
    "brand.logo_mode",
    "brand.visual_style",
    "a_roll.mode",
    "budget",
    "cleanup_policy",
    "collaboration",
)

CANDIDATE_AV_GATE_STAGES = {"candidate-internal-gate"}
FINAL_VISUAL_GATE_STAGES = {"editing-final"}
SCRIPT_STYLE_GATE_STAGES = {"scriptwriting"}
SUBTITLE_PHRASE_GATE_STAGES = {"editing-final"}
FIRST_FULL_CUT_GATE_STAGES = {"editing-first-full-cut"}
STORYBOARD_GATE_STAGES = {"storyboard"}
CANDIDATE_AV_CHECKS = (
    "visual_asset_policy",
    "subtitle_single_authority",
    "voice_pacing",
    "animation_sfx_audible",
    "bgm_audible",
    "chapter_navigation",
    "source_quality",
    "third_party_origin_uniqueness",
    "chapter_labels_and_segmentation_visual",
    "brand_overlay_visual",
    "source_perceived_quality",
    "short_shot_readability",
    "source_semantic_fit",
    "event_date_scope",
    "claim_visual_alignment",
)
G3_VISUAL_CHECKS = (
    "visual_asset_policy",
    "subtitle_single_authority",
    "chapter_labels_and_segmentation_visual",
    "brand_overlay_visual",
    "source_perceived_quality",
    "short_shot_readability",
)
G3_FACT_CHECKS = (
    "source_semantic_fit",
    "event_date_scope",
    "claim_visual_alignment",
)
FINAL_VISUAL_CHECKS = (
    "chapter_navigation_structure",
    "chapter_navigation_pixel_progress",
    "third_party_origin_uniqueness",
    "source_quality",
    "visual_asset_policy",
    "readable_visual_duration",
    "brand_overlay",
    "visual_timeline_coverage",
    "visual_semantic_contract",
    "third_party_coverage",
    "subtitle_pixel_presence",
    "third_party_image_uniqueness",
    "third_party_footage_mapping",
    "third_party_image_mapping",
    "third_party_source_appearance",
)
G3_REVIEW_ROLES = {
    "g3-director-review": "09-director-review",
    "g3-visual-review": "10-visual-review",
    "g3-fact-review": "11-fact-review",
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _nested(value: dict, dotted: str):
    current = value
    for part in dotted.split("."):
        if not isinstance(current, dict) or part not in current:
            raise ValueError(f"missing required brief field: {dotted}")
        current = current[part]
    return current


def validate_brief(brief: dict) -> None:
    if not isinstance(brief, dict):
        raise ValueError("brief must be an object")
    if brief.get("brief_confirmed") is not True:
        raise ValueError("brief_confirmed must be true and backed by human confirmation")
    for dotted in REQUIRED_BRIEF_PATHS:
        value = _nested(brief, dotted)
        if isinstance(value, str) and not value.strip():
            raise ValueError(f"brief field must not be empty: {dotted}")
    if not isinstance(brief["revision"], int) or brief["revision"] < 1:
        raise ValueError("revision must be a positive integer")
    duration = brief["duration"]
    if not isinstance(duration["target_seconds"], (int, float)) or duration["target_seconds"] <= 0:
        raise ValueError("duration.target_seconds must be positive")
    for name in ("tolerance_before_seconds", "tolerance_after_seconds"):
        if not isinstance(duration[name], (int, float)) or duration[name] < 0:
            raise ValueError(f"duration.{name} must be non-negative")
    forbidden = brief["visual"]["forbidden_asset_types"]
    if not isinstance(forbidden, list) or not all(isinstance(item, str) and item.strip() for item in forbidden):
        raise ValueError("visual.forbidden_asset_types must be a list of non-empty strings")


def _atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _append_event(path: Path, event: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(event, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


@contextmanager
def _locked(project: Path):
    folder = project / STATE_DIR
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / ".state.lock").open("a", encoding="utf-8") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        try:
            yield folder
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def initialize_project(project, brief: dict) -> dict:
    validate_brief(brief)
    project = Path(project).resolve()
    project.mkdir(parents=True, exist_ok=True)
    with _locked(project) as folder:
        state_file = folder / "state.json"
        if state_file.exists():
            raise ValueError(f"workflow state already exists: {state_file}")
        brief_file = folder / "brief.json"
        _atomic_json(brief_file, brief)
        brief_sha = sha256(brief_file)
        stages = {name: {"status": "NOT_STARTED", "artifacts": [], "updated_at": None} for name in STAGES}
        stages["brief"] = {
            "status": "READY",
            "artifacts": [{"path": str(brief_file), "sha256": brief_sha}],
            "evidence": brief["confirmation_basis"],
            "updated_at": now(),
        }
        state = {
            "schema_version": 2,
            "project": str(project),
            "brief": {
                "brief_id": brief["brief_id"],
                "revision": brief["revision"],
                "config_sha256": brief_sha,
                "path": str(brief_file),
            },
            "stages": stages,
            "updated_at": now(),
        }
        _atomic_json(state_file, state)
        _append_event(folder / "events.jsonl", {
            "event": "project_initialized",
            "at": now(),
            "brief_id": brief["brief_id"],
            "revision": brief["revision"],
            "config_sha256": brief_sha,
        })
        return state


def get_state(project, *, allow_artifact_mismatch_stages: set[str] | None = None) -> dict:
    project = Path(project).resolve()
    allow_artifact_mismatch_stages = allow_artifact_mismatch_stages or set()
    unknown_allowed = sorted(allow_artifact_mismatch_stages - set(STAGES))
    if unknown_allowed:
        raise ValueError("unknown artifact-mismatch replacement stages: " + ", ".join(unknown_allowed))
    state_file = project / STATE_DIR / "state.json"
    if not state_file.is_file():
        raise ValueError(f"workflow state not found: {state_file}")
    state = json.loads(state_file.read_text(encoding="utf-8"))
    if state.get("project") != str(project):
        raise ValueError("workflow state project identity mismatch")
    brief_file = Path(state["brief"]["path"])
    if not brief_file.is_file() or sha256(brief_file) != state["brief"]["config_sha256"]:
        raise ValueError("locked brief is missing or has changed")
    schema_version = state.get("schema_version")
    if schema_version not in (1, 2):
        raise ValueError(f"unsupported workflow state schema_version: {schema_version}")
    stages = state.get("stages")
    if not isinstance(stages, dict):
        raise ValueError("workflow state stages must be an object")
    unknown_stages = sorted(set(stages) - set(STAGES))
    if unknown_stages:
        raise ValueError("unknown stored workflow stages: " + ", ".join(unknown_stages))
    if schema_version == 2 and set(stages) != set(STAGES):
        missing = sorted(set(STAGES) - set(stages))
        raise ValueError("workflow state is missing schema v2 stages: " + ", ".join(missing))
    for stage, value in stages.items():
        if not isinstance(value, dict):
            raise ValueError(f"stored stage must be an object: {stage}")
        status = value.get("status")
        if status not in STORED_RESULTS:
            raise ValueError(f"unsupported stored stage status for {stage}: {status}")
        artifacts = value.get("artifacts", [])
        if not isinstance(artifacts, list):
            raise ValueError(f"stored stage artifacts must be a list: {stage}")
        for artifact in artifacts:
            if not isinstance(artifact, dict):
                raise ValueError(f"stored artifact must be an object: {stage}")
            path = Path(artifact.get("path", ""))
            if not path.is_file() or path.is_symlink():
                raise ValueError(f"stored artifact missing or not a regular file: {path}")
            if not path.resolve().is_relative_to(project):
                raise ValueError(f"stored artifact is outside project: {path}")
            if stage not in allow_artifact_mismatch_stages and (artifact.get("sha256") != sha256(path) or artifact.get("size", path.stat().st_size) != path.stat().st_size):
                raise ValueError(f"artifact identity mismatch for {stage}: {path}")
        if status == "READY":
            blocked = [name for name in STAGES[stage] if stages.get(name, {}).get("status") != "READY"]
            if blocked:
                raise ValueError(f"stored READY stage has non-READY dependencies for {stage}: " + ", ".join(blocked))
    if stages.get("storyboard", {}).get("status") == "READY" and "storyboard" not in allow_artifact_mismatch_stages:
        storyboard_artifacts = [Path(item["path"]) for item in stages["storyboard"].get("artifacts", [])]
        _storyboard_gate("storyboard", storyboard_artifacts, stages["storyboard"].get("artifacts", []), state)
    if stages.get("editing-final", {}).get("status") == "READY" and "editing-final" not in allow_artifact_mismatch_stages:
        editing_artifacts = [Path(item["path"]) for item in stages["editing-final"].get("artifacts", [])]
        _final_visual_gate("editing-final", editing_artifacts, stages["editing-final"]["artifacts"], state)
        candidate_media = _editing_candidate_identity(state)
        for review_stage in G3_REVIEW_ROLES:
            if review_stage in allow_artifact_mismatch_stages:
                continue
            review_value = stages.get(review_stage, {})
            if review_value.get("status") == "READY":
                if review_value.get("target_sha256") != candidate_media["sha256"]:
                    raise ValueError(f"stored {review_stage} target is not the current candidate video")
                _g3_review_gate(
                    review_stage,
                    [Path(item["path"]) for item in review_value.get("artifacts", [])],
                    candidate_media["sha256"],
                    candidate_media["duration_seconds"],
                )
        internal = stages.get("candidate-internal-gate", {})
        if internal.get("status") == "READY" and "candidate-internal-gate" not in allow_artifact_mismatch_stages:
            internal_paths = [Path(item["path"]) for item in internal.get("artifacts", [])]
            _candidate_av_gate("candidate-internal-gate", internal_paths, internal.get("artifacts", []), state)
        owner = stages.get("owner-review-ready", {})
        if owner.get("status") == "READY" and "owner-review-ready" not in allow_artifact_mismatch_stages:
            _owner_review_ready_gate([Path(item["path"]) for item in owner.get("artifacts", [])], state)
    return state


def migrate_state_v1(project) -> dict:
    """Explicitly preserve and normalize a legacy v1 state; never runs implicitly."""
    project = Path(project).resolve()
    with _locked(project) as folder:
        state_file = folder / "state.json"
        if not state_file.is_file():
            raise ValueError(f"workflow state not found: {state_file}")
        raw = state_file.read_bytes()
        state = json.loads(raw)
        if state.get("schema_version") != 1:
            raise ValueError("state migration requires schema_version 1")
        if state.get("project") != str(project):
            raise ValueError("workflow state project identity mismatch")
        brief = state.get("brief")
        if not isinstance(brief, dict):
            raise ValueError("legacy state is missing brief identity")
        brief_file = Path(brief.get("path", ""))
        if not brief_file.is_file() or sha256(brief_file) != brief.get("config_sha256"):
            raise ValueError("locked brief is missing or has changed")

        backup_sha = hashlib.sha256(raw).hexdigest()
        backup = folder / f"state.v1.{backup_sha[:16]}.json"
        if backup.exists():
            raise ValueError(f"legacy state backup already exists: {backup}")
        _atomic_json(backup, state)

        legacy_top = {
            key: state[key]
            for key in list(state)
            if key not in {"schema_version", "project", "brief", "stages", "updated_at", "extensions"}
        }
        for key in legacy_top:
            state.pop(key, None)
        extensions = state.get("extensions") if isinstance(state.get("extensions"), dict) else {}
        extensions["legacy_v1"] = legacy_top
        extensions["migration"] = {
            "at": now(),
            "backup": str(backup),
            "backup_sha256": sha256(backup),
        }
        state["extensions"] = extensions

        legacy_stages = state.get("stages")
        if not isinstance(legacy_stages, dict):
            raise ValueError("legacy state stages must be an object")
        migrated_stages = {}
        for stage in STAGES:
            value = legacy_stages.get(stage)
            if not isinstance(value, dict):
                migrated_stages[stage] = {"status": "NOT_STARTED", "artifacts": [], "updated_at": None}
                continue
            value = dict(value)
            notes = []
            if value.get("status") not in STORED_RESULTS:
                notes.append(f"legacy unsupported status normalized from {value.get('status')}")
                value["status"] = "REVISE"
            records = []
            for artifact in value.get("artifacts", []):
                if not isinstance(artifact, dict):
                    notes.append("legacy non-object artifact removed")
                    continue
                path = Path(artifact.get("path", ""))
                if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(project):
                    notes.append(f"legacy artifact unavailable and removed: {path}")
                    value["status"] = "REVISE"
                    continue
                current = {"path": str(path.resolve()), "sha256": sha256(path), "size": path.stat().st_size}
                if artifact.get("sha256") != current["sha256"] or artifact.get("size", current["size"]) != current["size"]:
                    notes.append(f"legacy artifact identity changed and was rebound during explicit migration: {path}")
                    value["status"] = "REVISE"
                records.append(current)
            value["artifacts"] = records
            if notes:
                prior = value.get("evidence", "")
                value["evidence"] = (prior + " | " if prior else "") + "; ".join(notes)
            migrated_stages[stage] = value
        hardened_v2_stages = [
            "editing-final",
            "g3-director-review",
            "g3-visual-review",
            "g3-fact-review",
            "candidate-internal-gate",
            "owner-review-ready",
            "delivery",
            "feedback",
        ]
        for stage in hardened_v2_stages:
            value = migrated_stages[stage]
            if value["status"] == "READY":
                value["status"] = "REVISE" if stage == "editing-final" else "STALE"
                value["stale_because"] = "v2-hard-gates-require-current-schema-evidence"
                prior = value.get("evidence", "")
                note = "legacy READY cannot be inherited across the v2 final-pixel and owner-review gates"
                value["evidence"] = (prior + " | " if prior else "") + note
                value["updated_at"] = now()
        for stage, dependencies in STAGES.items():
            if migrated_stages[stage]["status"] == "READY" and any(migrated_stages[name]["status"] != "READY" for name in dependencies):
                migrated_stages[stage]["status"] = "STALE"
                migrated_stages[stage]["stale_because"] = "v1-migration-dependency-check"
                migrated_stages[stage]["updated_at"] = now()

        state["schema_version"] = 2
        state["stages"] = migrated_stages
        state["updated_at"] = now()
        _atomic_json(state_file, state)
        _append_event(folder / "events.jsonl", {
            "event": "state_migrated",
            "at": now(),
            "from_schema_version": 1,
            "to_schema_version": 2,
            "backup": str(backup),
            "backup_sha256": sha256(backup),
        })
    return get_state(project)


def _descendants(stage: str) -> list[str]:
    found = set()
    frontier = [stage]
    while frontier:
        parent = frontier.pop()
        for candidate, dependencies in STAGES.items():
            if parent in dependencies and candidate not in found:
                found.add(candidate)
                frontier.append(candidate)
    return [name for name in STAGES if name in found]


def _artifact_records(project: Path, artifacts) -> list[dict]:
    if not isinstance(artifacts, (list, tuple)) or not artifacts:
        raise ValueError("READY requires at least one artifact")
    records = []
    for item in artifacts:
        path = Path(item).resolve()
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"artifact missing or not a regular file: {path}")
        if not path.is_relative_to(project):
            raise ValueError(f"artifact must be inside project: {path}")
        records.append({"path": str(path), "sha256": sha256(path), "size": path.stat().st_size})
    return records


def _json_reports(artifacts, schema: str, stage: str | None = None) -> list[tuple[Path, dict]]:
    reports = []
    for item in artifacts:
        path = Path(item).resolve()
        if path.suffix.lower() != ".json":
            continue
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if value.get("schema") == schema and (stage is None or value.get("stage") == stage):
            reports.append((path, value))
    return reports


def _candidate_media_from_records(records: list[dict]) -> dict:
    candidates = []
    for record in records:
        path = Path(record["path"])
        if path.suffix.lower() not in {".mp4", ".mov", ".mkv", ".webm"}:
            continue
        try:
            probe = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height", "-of", "json", str(path)],
                check=True,
                capture_output=True,
                text=True,
                timeout=60,
            )
            value = json.loads(probe.stdout)
            streams = value.get("streams") or []
            if any(item.get("codec_type") == "video" for item in streams):
                candidates.append({
                    **record,
                    "duration_seconds": float(value.get("format", {}).get("duration") or 0),
                    "has_audio": any(item.get("codec_type") == "audio" for item in streams),
                })
        except (OSError, ValueError, subprocess.SubprocessError, json.JSONDecodeError):
            continue
    if len(candidates) != 1 or candidates[0]["duration_seconds"] <= 0:
        raise ValueError("editing-final requires exactly one ffprobe-readable candidate video artifact")
    return candidates[0]


def _editing_candidate_identity(state: dict) -> dict:
    return _candidate_media_from_records(state["stages"]["editing-final"].get("artifacts", []))


def _locked_coverage_policy(state: dict) -> dict | None:
    brief = json.loads(Path(state["brief"]["path"]).read_text(encoding="utf-8"))
    visual = brief.get("visual")
    if not isinstance(visual, dict):
        return None
    primary = visual.get("third_party_primary_min_ratio")
    internal_video = visual.get("third_party_internal_video_min_ratio")
    if isinstance(primary, (int, float)) and isinstance(internal_video, (int, float)):
        return {"third_party_primary_min_ratio": float(primary), "third_party_internal_video_min_ratio": float(internal_video)}
    policy_text = visual.get("asset_policy")
    if not isinstance(policy_text, str):
        return None
    percentages = [float(item) / 100.0 for item in re.findall(r">=\s*(\d+(?:\.\d+)?)%", policy_text)]
    if len(percentages) < 2:
        return None
    return {"third_party_primary_min_ratio": percentages[0], "third_party_internal_video_min_ratio": percentages[1]}


def _storyboard_gate(stage: str, artifacts, records: list[dict], state: dict) -> dict:
    canonical = []
    records_by_path = {Path(item["path"]).resolve(): item for item in records}
    for item in artifacts:
        path = Path(item).resolve()
        if path.suffix.lower() != ".json":
            continue
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        schema = value.get("schema")
        if (
            isinstance(schema, str)
            and schema.startswith("swainwong.storyboard.")
            and isinstance(value.get("audience_visual_units"), list)
        ):
            canonical.append((path, value))
    if len(canonical) != 1:
        raise ValueError(f"{stage} READY requires exactly one canonical audience_visual_units storyboard artifact")
    path, storyboard = canonical[0]
    record = records_by_path.get(path)
    storyboard_hash = record.get("sha256") if isinstance(record, dict) else sha256(path)
    from storyboard_gate import validate_storyboard
    report = validate_storyboard(
        storyboard,
        project=Path(state["project"]),
        locked_policy=_locked_coverage_policy(state),
        storyboard_sha256=storyboard_hash,
    )
    if report.get("status") != "PASS" or report.get("failed_checks"):
        findings = report.get("findings")
        messages = [item.get("message") for item in findings if isinstance(item, dict) and isinstance(item.get("message"), str)] if isinstance(findings, list) else []
        raise ValueError("storyboard machine gate failed: " + ("; ".join(messages) if messages else "unknown deterministic failure"))
    return report


def _script_style_gate(stage: str, artifacts, records: list[dict]) -> dict:
    reports = _json_reports(artifacts, "swainwong.script-style-gate.v1")
    if len(reports) != 1:
        raise ValueError(f"{stage} READY requires exactly one script style gate report")
    _, report = reports[0]
    canonical = []
    for item in artifacts:
        path = Path(item).resolve()
        if path.suffix.lower() != ".json":
            continue
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(value.get("sentences"), list):
            canonical.append((path, value))
    if len(canonical) != 1:
        raise ValueError(f"{stage} READY requires exactly one canonical script JSON with sentences")
    script_path, payload = canonical[0]
    input_identity = report.get("input")
    if not isinstance(input_identity, dict) or Path(input_identity.get("path", "")).resolve() != script_path or input_identity.get("sha256") != sha256(script_path):
        raise ValueError("script style gate is not bound to the canonical script artifact")
    policy = report.get("policy")
    if not isinstance(policy, dict) or policy.get("max_meta_markers") != 2 or policy.get("max_rhetorical_questions") != 3:
        raise ValueError("script style gate policy cannot loosen the workflow defaults")
    from script_style_gate import evaluate_script
    recomputed = evaluate_script(
        payload,
        min_cjk_chars=policy.get("min_cjk_chars"),
        max_cjk_chars=policy.get("max_cjk_chars"),
        max_meta_markers=2,
        max_rhetorical_questions=3,
    )
    recomputed["input"] = input_identity
    if recomputed != report:
        raise ValueError("script style gate report does not match plugin recomputation")
    if report.get("status") != "PASS" or report.get("findings"):
        raise ValueError("script style gate must be PASS with no findings")
    return report


def _subtitle_phrase_gate(stage: str, artifacts, records: list[dict]) -> dict:
    reports = _json_reports(artifacts, "swainwong.subtitle-phrase-gate.v1")
    if len(reports) != 1:
        raise ValueError(f"{stage} READY requires exactly one subtitle phrase gate report")
    _, report = reports[0]
    inputs = report.get("inputs")
    policy = report.get("policy")
    if not isinstance(inputs, dict) or not isinstance(policy, dict):
        raise ValueError("subtitle phrase gate is missing inputs or policy")
    limits = {
        "max_duration": 4.5,
        "max_zh_chars": 20,
        "max_en_chars": 56,
        "max_zh_cps": 12.0,
        "max_en_cps": 24.0,
    }
    for key, maximum in limits.items():
        value = policy.get(key)
        if not isinstance(value, (int, float)) or value > maximum:
            raise ValueError(f"subtitle phrase gate policy cannot loosen {key}")
    resolved = {}
    artifact_paths = {Path(record["path"]).resolve(): record for record in records}
    for language in ("zh_vtt", "en_vtt"):
        identity = inputs.get(language)
        if not isinstance(identity, dict):
            raise ValueError(f"subtitle phrase gate missing {language} identity")
        path = Path(identity.get("path", "")).resolve()
        record = artifact_paths.get(path)
        if record is None or path.suffix.lower() != ".vtt" or identity.get("sha256") != record["sha256"]:
            raise ValueError(f"subtitle phrase gate {language} is not bound to a recorded VTT artifact")
        resolved[language] = path
    from subtitle_phrase_gate import evaluate_vtt_pair
    recomputed = evaluate_vtt_pair(
        resolved["zh_vtt"].read_text(encoding="utf-8"),
        resolved["en_vtt"].read_text(encoding="utf-8"),
        max_duration=float(policy["max_duration"]),
        max_zh_chars=int(policy["max_zh_chars"]),
        max_en_chars=int(policy["max_en_chars"]),
        max_zh_cps=float(policy["max_zh_cps"]),
        max_en_cps=float(policy["max_en_cps"]),
    )
    recomputed["inputs"] = inputs
    if recomputed != report:
        raise ValueError("subtitle phrase gate report does not match plugin recomputation")
    if report.get("status") != "PASS" or report.get("findings"):
        raise ValueError("subtitle phrase gate must be PASS with no findings")
    return report


def _final_visual_gate(stage: str, artifacts, records: list[dict], state: dict | None = None) -> dict:
    candidate_record = _candidate_media_from_records(records)
    inputs = _json_reports(artifacts, "swainwong.final-visual-gate-input.v2")
    if len(inputs) != 1:
        raise ValueError(f"{stage} READY requires exactly one final visual gate input manifest")
    input_path, manifest = inputs[0]
    if state is not None:
        locked_policy = _locked_coverage_policy(state)
        declared_policy = manifest.get("coverage_policy")
        if locked_policy is not None and declared_policy != locked_policy:
            raise ValueError("final visual gate coverage_policy does not match the locked brief")
    reports = _json_reports(artifacts, "swainwong.final-visual-gate.v2")
    if len(reports) != 1:
        raise ValueError(f"{stage} READY requires exactly one final visual gate report")
    path, report = reports[0]
    candidate = report.get("candidate")
    if not isinstance(candidate, dict):
        raise ValueError("final visual gate is missing candidate identity")
    candidate_sha = candidate.get("sha256")
    if not isinstance(candidate_sha, str) or candidate_sha != candidate_record["sha256"]:
        raise ValueError("final visual gate sha256 is not bound to the recorded candidate video")
    if Path(manifest.get("candidate", {}).get("path", "")).resolve() != Path(candidate_record["path"]).resolve():
        raise ValueError("final visual gate input candidate path is not the recorded candidate video")
    from final_visual_gate import validate_manifest
    recomputed = validate_manifest(manifest, input_manifest_sha256=sha256(input_path))
    if report != recomputed:
        raise ValueError("final visual gate report does not match plugin recomputation from actual media")
    if report.get("status") != "PASS" or report.get("failed_checks") != []:
        raise ValueError("final visual gate must be PASS with no failed checks")
    summary = report.get("summary")
    if not isinstance(summary, dict):
        raise ValueError("final visual gate summary is missing")
    failed = [name for name in FINAL_VISUAL_CHECKS if not isinstance(summary.get(name), dict) or summary[name].get("status") != "PASS"]
    if failed:
        raise ValueError("final visual gate checks not PASS: " + ", ".join(failed))
    return report


def _review_report_from_state(state: dict, stage: str) -> tuple[dict, str]:
    reports = []
    for artifact in state["stages"][stage].get("artifacts", []):
        path = Path(artifact["path"])
        if path.suffix.lower() != ".json":
            continue
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if value.get("schema") == "swainwong.review.v1" and value.get("stage") == stage:
            reports.append((value, artifact["sha256"]))
    if len(reports) != 1:
        raise ValueError(f"{stage} must contain exactly one structured review report")
    return reports[0]


def _candidate_av_gate(stage: str, artifacts, records: list[dict], state: dict) -> dict:
    reports = _json_reports(artifacts, "swainwong.candidate-av-gate.v1", stage)
    if len(reports) != 1:
        raise ValueError(f"{stage} READY requires exactly one candidate AV gate report")
    path, report = reports[0]
    candidate = report.get("candidate")
    if not isinstance(candidate, dict):
        raise ValueError("candidate AV gate is missing candidate identity")
    candidate_sha = candidate.get("sha256")
    duration = candidate.get("duration_seconds")
    candidate_media = _editing_candidate_identity(state)
    if not isinstance(candidate_sha, str) or candidate_sha != candidate_media["sha256"]:
        raise ValueError("candidate AV gate sha256 is not bound to the current editing-final candidate")
    if not isinstance(duration, (int, float)) or abs(duration - candidate_media["duration_seconds"]) > 0.05:
        raise ValueError("candidate AV gate duration_seconds must be positive")
    review = report.get("review")
    if not isinstance(review, dict):
        raise ValueError("candidate AV gate is missing review evidence")
    for mode in ("visual", "audio"):
        evidence = review.get(mode)
        if not isinstance(evidence, dict) or evidence.get("status") != "PASS":
            raise ValueError(f"candidate AV gate {mode} review must be PASS")
        reviewer = evidence.get("reviewer")
        method = evidence.get("method")
        coverage = evidence.get("coverage_seconds")
        if not isinstance(reviewer, str) or not reviewer.strip():
            raise ValueError(f"candidate AV gate {mode} reviewer is required")
        if not isinstance(coverage, (int, float)) or coverage + 0.01 < duration:
            raise ValueError(f"candidate AV gate {mode} coverage must include the complete candidate")
        if method != "continuous-normal-speed-final-file-review":
            raise ValueError(f"candidate AV gate {mode} method must be continuous-normal-speed-final-file-review")
    checks = report.get("checks")
    if not isinstance(checks, dict):
        raise ValueError("candidate AV gate checks are missing")
    failed = [name for name in CANDIDATE_AV_CHECKS if checks.get(name) != "PASS"]
    if failed:
        raise ValueError("candidate AV gate checks not PASS: " + ", ".join(failed))
    findings = report.get("findings")
    if not isinstance(findings, list) or findings:
        raise ValueError("candidate AV gate has unresolved findings")
    producer_id = report.get("producer_id")
    if not isinstance(producer_id, str) or not producer_id.strip():
        raise ValueError("candidate AV gate producer_id is required")
    report_hashes = report.get("review_reports")
    if not isinstance(report_hashes, dict) or set(report_hashes) != set(G3_REVIEW_ROLES):
        raise ValueError("candidate AV gate must bind all three G3 review reports")
    reviewers = []
    structured = {}
    for review_stage in G3_REVIEW_ROLES:
        review_report, review_sha = _review_report_from_state(state, review_stage)
        if report_hashes.get(review_stage) != review_sha:
            raise ValueError(f"candidate AV gate review report hash mismatch: {review_stage}")
        if review_report.get("candidate_sha256") != candidate_sha:
            raise ValueError(f"candidate AV gate review targets another candidate: {review_stage}")
        reviewer_id = review_report.get("reviewer_id")
        if reviewer_id == producer_id:
            raise ValueError(f"candidate AV gate reviewer cannot be the producer: {review_stage}")
        reviewers.append(reviewer_id)
        structured[review_stage] = review_report
    if len(reviewers) != len(set(reviewers)):
        raise ValueError("candidate AV gate G3 reviewers must be distinct")
    if review["visual"]["reviewer"] != structured["g3-visual-review"]["reviewer_id"]:
        raise ValueError("candidate AV gate visual reviewer must match the structured G3 visual report")
    if review["audio"]["reviewer"] != structured["g3-director-review"]["reviewer_id"]:
        raise ValueError("candidate AV gate audio reviewer must match the structured G3 director report")
    visual_checks = structured["g3-visual-review"].get("visual_checks")
    if not isinstance(visual_checks, dict) or any(visual_checks.get(name) != "PASS" for name in G3_VISUAL_CHECKS):
        raise ValueError("candidate AV gate requires all structured G3 visual checks to PASS")
    if any(checks.get(name) != visual_checks.get(name) for name in G3_VISUAL_CHECKS):
        raise ValueError("candidate AV gate visual checks must match the structured G3 visual report")
    fact_checks = structured["g3-fact-review"].get("fact_checks")
    if not isinstance(fact_checks, dict) or any(fact_checks.get(name) != "PASS" for name in G3_FACT_CHECKS):
        raise ValueError("candidate AV gate requires all structured G3 fact checks to PASS")
    if any(checks.get(name) != fact_checks.get(name) for name in G3_FACT_CHECKS):
        raise ValueError("candidate AV gate fact checks must match the structured G3 fact report")
    return report


def _g3_review_gate(stage: str, artifacts, target_sha256: str, candidate_duration: float) -> dict:
    reports = _json_reports(artifacts, "swainwong.review.v1", stage)
    if len(reports) != 1:
        raise ValueError(f"{stage} READY requires exactly one structured review report")
    _, report = reports[0]
    if report.get("role") != G3_REVIEW_ROLES[stage]:
        raise ValueError(f"{stage} review role mismatch")
    if report.get("candidate_sha256") != target_sha256:
        raise ValueError(f"{stage} review candidate sha256 mismatch")
    reviewer = report.get("reviewer_id")
    producer = report.get("producer_id")
    if not isinstance(reviewer, str) or not reviewer.strip() or not isinstance(producer, str) or not producer.strip():
        raise ValueError(f"{stage} reviewer_id and producer_id are required")
    if reviewer == producer:
        raise ValueError(f"{stage} reviewer must be independent of the producer")
    if report.get("method") != "continuous-normal-speed-final-file-review":
        raise ValueError(f"{stage} method must be continuous-normal-speed-final-file-review")
    coverage = report.get("coverage")
    if not isinstance(coverage, dict) or coverage.get("start_seconds") not in (0, 0.0):
        raise ValueError(f"{stage} coverage must start at zero")
    end = coverage.get("end_seconds")
    if not isinstance(end, (int, float)) or end + 0.01 < candidate_duration:
        raise ValueError(f"{stage} coverage must include the complete candidate")
    capabilities = report.get("capabilities")
    if not isinstance(capabilities, dict):
        raise ValueError(f"{stage} capabilities are required")
    required_capability = {
        "g3-director-review": "real_listening",
        "g3-visual-review": "continuous_visual",
        "g3-fact-review": "fact_and_source_review",
    }[stage]
    if capabilities.get(required_capability) is not True:
        raise ValueError(f"{stage} requires capability {required_capability}")
    if report.get("status") != "PASS" or report.get("findings") != []:
        raise ValueError(f"{stage} must be PASS with no unresolved findings")
    if stage == "g3-visual-review":
        checks = report.get("visual_checks")
        if not isinstance(checks, dict):
            raise ValueError("g3-visual-review requires explicit visual_checks")
        failed = [name for name in G3_VISUAL_CHECKS if checks.get(name) != "PASS"]
        if failed:
            raise ValueError("g3-visual-review visual checks not PASS: " + ", ".join(failed))
    if stage == "g3-fact-review":
        checks = report.get("fact_checks")
        if not isinstance(checks, dict):
            raise ValueError("g3-fact-review requires explicit fact_checks")
        failed = [name for name in G3_FACT_CHECKS if checks.get(name) != "PASS"]
        if failed:
            raise ValueError("g3-fact-review fact checks not PASS: " + ", ".join(failed))
    return report


def _owner_review_ready_gate(artifacts, state: dict) -> dict:
    reports = _json_reports(artifacts, "swainwong.owner-review-ready.v1")
    if len(reports) != 1:
        raise ValueError("owner-review-ready requires exactly one readiness report")
    _, report = reports[0]
    candidate_sha = report.get("candidate_sha256")
    candidate_media = _editing_candidate_identity(state)
    if candidate_sha != candidate_media["sha256"]:
        raise ValueError("owner-review-ready candidate is not the current editing-final candidate")
    gate_sha = report.get("candidate_internal_gate_sha256")
    gate_hashes = {item["sha256"] for item in state["stages"]["candidate-internal-gate"].get("artifacts", [])}
    if gate_sha not in gate_hashes:
        raise ValueError("owner-review-ready is not bound to the current candidate internal gate")
    return report


def _first_full_cut_gate(stage: str, artifacts, records: list[dict], state: dict) -> dict:
    reports = []
    for item in artifacts:
        path = Path(item).resolve()
        if path.suffix.lower() != ".json":
            continue
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if value.get("schema") == "swainwong.first-full-cut.v1" and value.get("stage") == stage:
            reports.append((path, value))
    if len(reports) != 1:
        raise ValueError(f"{stage} READY requires exactly one first full cut report")
    path, report = reports[0]
    candidate = report.get("candidate")
    if not isinstance(candidate, dict):
        raise ValueError("first full cut report is missing candidate identity")
    candidate_sha = candidate.get("sha256")
    duration = candidate.get("duration_seconds")
    candidate_media = _candidate_media_from_records(records)
    if not isinstance(candidate_sha, str) or candidate_sha != candidate_media["sha256"]:
        raise ValueError("first full cut sha256 is not bound to a recorded candidate artifact")
    if not isinstance(duration, (int, float)) or duration <= 0:
        raise ValueError("first full cut duration_seconds must be positive")
    if abs(float(duration) - candidate_media["duration_seconds"]) > 0.05:
        raise ValueError("first full cut duration_seconds does not match the playable candidate")
    if candidate_media["has_audio"] is not True:
        raise ValueError("first full cut requires an actual audio stream")

    brief = json.loads(Path(state["brief"]["path"]).read_text(encoding="utf-8"))
    duration_contract = brief["duration"]
    minimum = duration_contract["target_seconds"] - duration_contract["tolerance_before_seconds"]
    maximum = duration_contract["target_seconds"] + duration_contract["tolerance_after_seconds"]
    if duration < minimum or duration > maximum:
        raise ValueError(f"first full cut duration {duration} is outside locked range {minimum}..{maximum}")

    script_hashes = {
        item["sha256"] for item in state["stages"]["scriptwriting"].get("artifacts", [])
    }
    if report.get("script_sha256") not in script_hashes:
        raise ValueError("first full cut is not bound to the production-ready script")

    coverage = report.get("coverage")
    if not isinstance(coverage, dict):
        raise ValueError("first full cut coverage is missing")
    if coverage.get("start_seconds") not in (0, 0.0):
        raise ValueError("first full cut must start at zero")
    end_seconds = coverage.get("end_seconds")
    if not isinstance(end_seconds, (int, float)) or end_seconds + 0.01 < duration:
        raise ValueError("first full cut coverage must reach the candidate end")
    if coverage.get("missing_ranges") != []:
        raise ValueError("first full cut cannot contain missing timeline ranges")

    technical = report.get("technical")
    required_technical = {
        "render_complete": True,
        "decode_status": "PASS",
        "audio_clock_present": True,
        "visual_track_present": True,
    }
    if not isinstance(technical, dict):
        raise ValueError("first full cut technical evidence is missing")
    failed = [name for name, expected in required_technical.items() if technical.get(name) != expected]
    if failed:
        raise ValueError("first full cut technical checks not satisfied: " + ", ".join(failed))
    if not isinstance(report.get("placeholders"), list):
        raise ValueError("first full cut placeholders must be an explicit list")
    return report


def record_stage(project, stage: str, status: str, artifacts=None, *, evidence: str, target_sha256=None) -> dict:
    project = Path(project).resolve()
    if stage == "brief" or stage not in STAGES:
        raise ValueError(f"unknown or immutable stage: {stage}")
    if status not in ALLOWED_RESULTS:
        raise ValueError(f"unsupported stage status: {status}")
    if not isinstance(evidence, str) or not evidence.strip():
        raise ValueError("stage result requires evidence")
    with _locked(project) as folder:
        state = get_state(project, allow_artifact_mismatch_stages={stage, *_descendants(stage)})
        if status == "READY":
            blocked = [name for name in STAGES[stage] if state["stages"][name]["status"] != "READY"]
            if blocked:
                raise ValueError("dependencies not READY: " + ", ".join(blocked))
            records = _artifact_records(project, artifacts)
            if stage in CANDIDATE_AV_GATE_STAGES:
                _candidate_av_gate(stage, artifacts, records, state)
            if stage in FINAL_VISUAL_GATE_STAGES:
                _final_visual_gate(stage, artifacts, records, state)
            if stage in SCRIPT_STYLE_GATE_STAGES:
                _script_style_gate(stage, artifacts, records)
            if stage in SUBTITLE_PHRASE_GATE_STAGES:
                _subtitle_phrase_gate(stage, artifacts, records)
            if stage in FIRST_FULL_CUT_GATE_STAGES:
                _first_full_cut_gate(stage, artifacts, records, state)
            if stage in STORYBOARD_GATE_STAGES:
                _storyboard_gate(stage, artifacts, records, state)
            if stage == "owner-review-ready":
                _owner_review_ready_gate(artifacts, state)
        else:
            records = _artifact_records(project, artifacts) if artifacts else []
        if stage.startswith(("g1-", "g2-", "g3-")) and stage.endswith("-review"):
            if not isinstance(target_sha256, str) or not target_sha256:
                raise ValueError("review stage requires target_sha256")
            dependency_hashes = {
                item["sha256"]
                for dependency in STAGES[stage]
                for item in state["stages"][dependency].get("artifacts", [])
            }
            if target_sha256 not in dependency_hashes:
                raise ValueError("review target_sha256 is not a current dependency artifact")
            if status == "READY" and stage in G3_REVIEW_ROLES:
                candidate_media = _editing_candidate_identity(state)
                if target_sha256 != candidate_media["sha256"]:
                    raise ValueError("G3 review target_sha256 must be the current candidate video")
                _g3_review_gate(stage, artifacts, target_sha256, candidate_media["duration_seconds"])
        previous = state["stages"][stage]
        changed = previous.get("status") != "NOT_STARTED" and (
            previous.get("status") != status
            or previous.get("artifacts", []) != records
            or previous.get("target_sha256") != target_sha256
        )
        state["stages"][stage] = {
            "status": status,
            "artifacts": records,
            "evidence": evidence.strip(),
            "target_sha256": target_sha256,
            "updated_at": now(),
        }
        invalidated = []
        if changed:
            for name in _descendants(stage):
                if state["stages"][name]["status"] != "NOT_STARTED":
                    rebound_artifacts = []
                    for artifact in state["stages"][name].get("artifacts", []):
                        path = Path(artifact["path"])
                        rebound_artifacts.append({
                            "path": str(path),
                            "sha256": sha256(path),
                            "size": path.stat().st_size,
                        })
                    state["stages"][name] = {
                        **state["stages"][name],
                        "status": "STALE",
                        "artifacts": rebound_artifacts,
                        "stale_because": stage,
                        "updated_at": now(),
                    }
                    invalidated.append(name)
        state["updated_at"] = now()
        _atomic_json(folder / "state.json", state)
        _append_event(folder / "events.jsonl", {
            "event": "stage_recorded",
            "at": now(),
            "stage": stage,
            "status": status,
            "brief_sha256": state["brief"]["config_sha256"],
            "artifact_sha256": [item["sha256"] for item in records],
            "target_sha256": target_sha256,
            "invalidated_stages": invalidated,
        })
        return state


def build_task_packet(project, role: str) -> dict:
    if role not in ROLE_STAGES:
        raise ValueError(f"unknown role: {role}")
    state = get_state(project)
    candidates = ROLE_STAGES[role]
    stage = next((name for name in candidates if state["stages"][name]["status"] != "READY"), candidates[-1])
    dependencies = {name: state["stages"][name] for name in STAGES[stage]}
    role_root = SKILL_ROOT / "roles" / role
    method = role_root / "METHOD.md"
    harness = role_root / "HARNESS.md"
    if not method.is_file() or not harness.is_file():
        raise ValueError(f"role module is incomplete: {role}")
    return {
        "schema_version": 1,
        "role": role,
        "stage": stage,
        "dispatchable": all(item["status"] == "READY" for item in dependencies.values()),
        "brief": state["brief"],
        "role_method": str(method),
        "role_harness": str(harness),
        "dependencies": dependencies,
        "allowed_results": sorted(ALLOWED_RESULTS),
        "return_contract": [
            "input brief identity",
            "actual completed scope",
            "artifact paths and hashes",
            "evidence",
            "uncovered items",
            "downstream impact",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init")
    init.add_argument("--project", type=Path, required=True)
    init.add_argument("--brief", type=Path, required=True)
    status = commands.add_parser("status")
    status.add_argument("--project", type=Path, required=True)
    migrate = commands.add_parser("migrate-v1")
    migrate.add_argument("--project", type=Path, required=True)
    packet = commands.add_parser("task-packet")
    packet.add_argument("--project", type=Path, required=True)
    packet.add_argument("--role", required=True)
    record = commands.add_parser("record")
    record.add_argument("--project", type=Path, required=True)
    record.add_argument("--stage", required=True)
    record.add_argument("--status", required=True)
    record.add_argument("--artifact", type=Path, action="append", default=[])
    record.add_argument("--evidence", required=True)
    record.add_argument("--target-sha256")
    args = parser.parse_args()
    if args.command == "init":
        result = initialize_project(args.project, json.loads(args.brief.read_text(encoding="utf-8")))
    elif args.command == "status":
        result = get_state(args.project)
    elif args.command == "migrate-v1":
        result = migrate_state_v1(args.project)
    elif args.command == "task-packet":
        result = build_task_packet(args.project, args.role)
    else:
        result = record_stage(
            args.project,
            args.stage,
            args.status,
            args.artifact,
            evidence=args.evidence,
            target_sha256=args.target_sha256,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
