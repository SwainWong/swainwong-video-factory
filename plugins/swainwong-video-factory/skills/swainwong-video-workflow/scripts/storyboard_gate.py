#!/usr/bin/env python3
"""Deterministic machine gate for canonical audience-visual-unit storyboards.

This gate validates structural and file-backed facts only. It deliberately does
not judge creative quality and cannot replace an independent G1 visual review.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
from typing import Any


SCHEMA = "swainwong.storyboard-gate.v1"
WORKFLOW_CONTRACT_VERSION = "4.9"
TIME_TOLERANCE = 0.002
PROBE_TOLERANCE = 1e-7
RATIO_TOLERANCE = 1e-6
FIXED_FIVE_SECOND_SHARE_LIMIT = 0.10
DIRECT_STATUS = "direct_evidence"
NON_DIRECT_STATUSES = {"contextual", "illustrative_only", "original_explanation"}
FORBIDDEN_PRIMARY_TYPES = {
    "svg",
    "code-vector",
    "code-vector-as-primary-content",
    "generic-vector-illustration",
    "large-placeholder-infographic",
    "vector-static",
}
THIRD_PARTY_VIDEO_TYPES = {"third-party-footage", "third-party-video"}
THIRD_PARTY_IMAGE_TYPES = {"third-party-image"}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normal_type(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return "-".join(value.strip().lower().replace("_", "-").split())


def _nonempty(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, dict):
        return bool(value)
    return value is not None


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _timeline(item: dict) -> tuple[float, float] | None:
    timeline = item.get("timeline")
    if not isinstance(timeline, dict):
        timeline = item
    start = _number(timeline.get("start_seconds"))
    end = _number(timeline.get("end_seconds"))
    if start is None or end is None:
        return None
    return start, end


def _close(left: float, right: float, tolerance: float = TIME_TOLERANCE) -> bool:
    return abs(left - right) <= tolerance


def _inside_project(project: Path, value: Any) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        return None
    path = Path(value)
    if not path.is_absolute():
        path = project / path
    try:
        resolved = path.resolve(strict=True)
    except (OSError, RuntimeError):
        return None
    if path.is_symlink() or not resolved.is_file() or not resolved.is_relative_to(project):
        return None
    return resolved


def _error(errors: list[dict], check: str, message: str) -> None:
    errors.append({"check": check, "message": message})


def _validate_receipt(receipt: Any, project: Path, errors: list[dict], location: str) -> None:
    if not isinstance(receipt, dict):
        _error(errors, "capture_receipt", f"capture receipt must be an object: {location}")
        return
    opened_at = receipt.get("opened_at")
    try:
        if not isinstance(opened_at, str) or not opened_at.strip():
            raise ValueError
        datetime.fromisoformat(opened_at.replace("Z", "+00:00"))
    except ValueError:
        _error(errors, "capture_receipt", f"capture receipt opened_at must be an ISO timestamp: {location}")
    response_status = receipt.get("response_status")
    if isinstance(response_status, bool) or not isinstance(response_status, int) or not 200 <= response_status < 400:
        _error(errors, "capture_receipt", f"capture receipt response_status must be 2xx or 3xx: {location}")
    for field in ("final_url_or_file", "exact_locator"):
        if not isinstance(receipt.get(field), str) or not receipt[field].strip():
            _error(errors, "capture_receipt", f"capture receipt {field} is required: {location}")
    capture = _inside_project(project, receipt.get("capture_path"))
    if capture is None:
        _error(errors, "capture_receipt", f"capture receipt capture_path must be a project-internal regular file: {location}")
        return
    expected = receipt.get("capture_sha256")
    if not isinstance(expected, str) or len(expected) != 64 or expected.lower() != _sha256(capture):
        _error(errors, "capture_receipt", f"capture receipt capture_sha256 does not match actual bytes: {location}")


def _validate_progress(storyboard: dict, body_end: float, total_end: float, errors: list[dict]) -> None:
    layers = storyboard.get("persistent_layers")
    progress = layers.get("progress") if isinstance(layers, dict) else None
    if not isinstance(progress, dict):
        _error(errors, "chapter_progress", "chapter progress contract is required")
        return
    canvas = progress.get("canvas")
    width = _number(canvas.get("width")) if isinstance(canvas, dict) else None
    declared_total = _number(canvas.get("total_duration_seconds")) if isinstance(canvas, dict) else None
    if width is None or width <= 0 or declared_total is None or not _close(declared_total, total_end):
        _error(errors, "chapter_progress", "chapter progress canvas must bind the actual total duration")
        return
    global_fill = progress.get("global_fill")
    if not isinstance(global_fill, dict) or global_fill.get("reset_per_shot") is not False:
        _error(errors, "chapter_progress", "chapter progress global fill must set reset_per_shot=false")

    segments = progress.get("segments")
    parsed_segments: list[tuple[str, float, float]] = []
    if not isinstance(segments, list) or not segments:
        _error(errors, "chapter_progress", "chapter progress segments are required")
        return
    cursor = 0.0
    for index, segment in enumerate(segments):
        interval = _timeline(segment) if isinstance(segment, dict) else None
        chapter_id = segment.get("chapter_id") if isinstance(segment, dict) else None
        if interval is None or not isinstance(chapter_id, str) or not chapter_id.strip():
            _error(errors, "chapter_progress", f"chapter progress segment {index} is invalid")
            continue
        start, end = interval
        if not _close(start, cursor) or end <= start:
            _error(errors, "chapter_progress", f"chapter progress segments must be contiguous at index {index}")
        parsed_segments.append((chapter_id, start, end))
        cursor = end
    if not parsed_segments or not _close(cursor, total_end):
        _error(errors, "chapter_progress", "chapter progress segments must cover the complete film including credits")
        return
    if not any(_close(start, body_end) for _, start, _ in parsed_segments):
        _error(errors, "chapter_progress", "chapter progress must contain the real body-to-credits boundary")

    actual_boundaries = [end for _, _, end in parsed_segments[:-1]]
    declared_boundaries = progress.get("actual_chapter_boundaries_seconds")
    if (
        not isinstance(declared_boundaries, list)
        or len(declared_boundaries) != len(actual_boundaries)
        or any(_number(value) is None or not _close(float(value), actual) for value, actual in zip(declared_boundaries, actual_boundaries))
    ):
        _error(errors, "chapter_progress", "chapter progress actual boundaries must match real segment boundaries")

    epsilon = _number(progress.get("boundary_epsilon_seconds"))
    required = progress.get("required_boundary_tests_seconds")
    expectations = progress.get("boundary_expectations")
    if epsilon is None or epsilon <= 0 or not isinstance(required, list) or not isinstance(expectations, list):
        _error(errors, "chapter_progress", "chapter progress boundary epsilon and probes are required")
        return
    required_values = [_number(value) for value in required]
    if any(value is None for value in required_values):
        _error(errors, "chapter_progress", "chapter progress required probe times must be numeric")
        return
    parsed_expectations: list[tuple[float, dict]] = []
    for item in expectations:
        t = _number(item.get("t")) if isinstance(item, dict) else None
        if t is not None:
            parsed_expectations.append((t, item))

    for boundary_index, boundary in enumerate(actual_boundaries):
        previous_id = parsed_segments[boundary_index][0]
        next_id = parsed_segments[boundary_index + 1][0]
        for offset, active_id in ((-epsilon, previous_id), (0.0, next_id), (epsilon, next_id)):
            expected_t = boundary + offset
            if not any(abs(value - expected_t) <= PROBE_TOLERANCE for value in required_values if value is not None):
                _error(errors, "chapter_progress", f"chapter progress is missing required boundary probe at {expected_t:g}")
                continue
            matches = [item for t, item in parsed_expectations if abs(t - expected_t) <= PROBE_TOLERANCE]
            if len(matches) != 1:
                _error(errors, "chapter_progress", f"chapter progress is missing a unique boundary expectation at {expected_t:g}")
                continue
            item = matches[0]
            fill = _number(item.get("global_fill_px"))
            expected_fill = width * expected_t / total_end
            if fill is None or abs(fill - expected_fill) > 0.01:
                _error(errors, "chapter_progress", f"chapter progress global fill is incorrect at {expected_t:g}")
            if item.get("active_segment") != active_id or item.get("reset_observed") is not False:
                _error(errors, "chapter_progress", f"chapter progress segment/reset expectation is incorrect at {expected_t:g}")


def validate_storyboard(
    storyboard: Any,
    *,
    project: str | Path,
    locked_policy: dict | None = None,
    storyboard_sha256: str | None = None,
) -> dict:
    """Return a deterministic PASS/FAIL report for a canonical storyboard."""
    project_path = Path(project).resolve()
    errors: list[dict] = []
    if not isinstance(storyboard, dict):
        _error(errors, "canonical_schema", "storyboard must be a JSON object")
        return _report(errors, storyboard_sha256)
    if storyboard.get("workflow_contract_version") != WORKFLOW_CONTRACT_VERSION:
        _error(errors, "workflow_contract", f"workflow contract must be {WORKFLOW_CONTRACT_VERSION}")
    if storyboard.get("role_status") != "READY":
        _error(errors, "role_status", "storyboard role_status must be READY")

    units = storyboard.get("audience_visual_units")
    if not isinstance(units, list) or not units:
        _error(errors, "unit_contract", "unit contract requires non-empty audience_visual_units")
        return _report(errors, storyboard_sha256)

    parsed_units: list[tuple[dict, float, float]] = []
    unit_ids: set[str] = set()
    origins: dict[str, list[tuple[float, float, str]]] = {}
    cursor = 0.0
    third_party_seconds = 0.0
    third_party_video_seconds = 0.0
    exact_five_seconds = 0
    for index, unit in enumerate(units):
        if not isinstance(unit, dict):
            _error(errors, "unit_contract", f"unit contract requires an object at index {index}")
            continue
        unit_id = unit.get("unit_id")
        primary_type = _normal_type(unit.get("primary_type"))
        sentence_ids = unit.get("sentence_ids")
        semantic_status = unit.get("semantic_status")
        event_date_scope = unit.get("event_date_scope")
        if (
            not isinstance(unit_id, str)
            or not unit_id.strip()
            or unit_id in unit_ids
            or not primary_type
            or not isinstance(sentence_ids, list)
            or not sentence_ids
            or not all(isinstance(value, str) and value.strip() for value in sentence_ids)
            or semantic_status not in ({DIRECT_STATUS} | NON_DIRECT_STATUSES)
            or not _nonempty(event_date_scope)
        ):
            _error(errors, "unit_contract", f"unit contract fields are missing or invalid at index {index}")
        if isinstance(unit_id, str):
            unit_ids.add(unit_id)
        interval = _timeline(unit)
        if interval is None:
            _error(errors, "timeline", f"timeline is missing for unit {unit_id or index}")
            continue
        start, end = interval
        duration = end - start
        declared_duration = _number(unit.get("timeline", {}).get("duration_seconds")) if isinstance(unit.get("timeline"), dict) else None
        if not _close(start, cursor) or end <= start or (declared_duration is not None and not _close(declared_duration, duration)):
            _error(errors, "timeline", f"timeline must be positive and contiguous at unit {unit_id or index}")
        cursor = end
        parsed_units.append((unit, start, end))
        if abs(duration - 5.0) <= RATIO_TOLERANCE:
            exact_five_seconds += 1

        if primary_type in FORBIDDEN_PRIMARY_TYPES or ("vector" in primary_type and primary_type != "original-raster"):
            _error(errors, "forbidden_primary", f"forbidden primary visual type: {unit.get('primary_type')}")
        coverage_class = unit.get("coverage_class")
        is_third_party = coverage_class == "third_party_primary" and primary_type in (THIRD_PARTY_VIDEO_TYPES | THIRD_PARTY_IMAGE_TYPES)
        if is_third_party:
            third_party_seconds += duration
            if primary_type in THIRD_PARTY_VIDEO_TYPES:
                third_party_video_seconds += duration

        unit_origins = unit.get("evidence_overlay_origin_ids")
        if not isinstance(unit_origins, list):
            _error(errors, "unit_contract", f"unit contract evidence_overlay_origin_ids must be a list: {unit_id or index}")
            unit_origins = []
        for origin in unit_origins:
            if isinstance(origin, str) and origin.strip():
                origins.setdefault(origin, []).append((start, end, unit_id or str(index)))

        visible = unit.get("visible_evidence")
        if not isinstance(visible, list):
            _error(errors, "visible_evidence", f"visible evidence must be a list: {unit_id or index}")
            visible = []
        if semantic_status == DIRECT_STATUS:
            claims = unit.get("claim_ids")
            sources = unit.get("fact_source_ids")
            if not isinstance(claims, list) or not claims or not isinstance(sources, list) or not sources or not unit_origins or not visible:
                _error(errors, "direct_evidence", f"direct evidence requires claim, fact source, evidence origin and visible evidence: {unit_id or index}")
            for visible_index, row in enumerate(visible):
                location = f"{unit_id or index}.visible_evidence[{visible_index}]"
                if not isinstance(row, dict):
                    _error(errors, "direct_evidence", f"direct evidence row must be an object: {location}")
                    continue
                if row.get("claim_id") not in (claims or []):
                    _error(errors, "direct_evidence", f"direct evidence claim is not bound to its unit: {location}")
                if row.get("fact_source_id") not in (sources or []):
                    _error(errors, "direct_evidence", f"direct evidence fact source is not bound to its unit: {location}")
                if row.get("evidence_origin_id") not in unit_origins:
                    _error(errors, "direct_evidence", f"direct evidence origin is not bound to its unit: {location}")
                if not _nonempty(row.get("locator_or_crop")) or not _nonempty(row.get("date_scope")):
                    _error(errors, "direct_evidence", f"direct evidence locator and date scope are required: {location}")
                on_start = _number(row.get("on_screen_start_seconds"))
                on_end = _number(row.get("on_screen_end_seconds"))
                if on_start is not None or on_end is not None:
                    if on_start is None or on_end is None or on_start < start - TIME_TOLERANCE or on_end > end + TIME_TOLERANCE or on_end <= on_start:
                        _error(errors, "direct_evidence", f"direct evidence visible interval must stay inside its unit: {location}")
                receipts = row.get("capture_receipts")
                if not isinstance(receipts, list) or not receipts:
                    _error(errors, "capture_receipt", f"capture receipt is required inline with direct evidence: {location}")
                else:
                    for receipt_index, receipt in enumerate(receipts):
                        _validate_receipt(receipt, project_path, errors, f"{location}.capture_receipts[{receipt_index}]")
        elif visible:
            _error(errors, "visible_evidence", f"visible evidence is forbidden on non-direct unit {unit_id or index}")

    if not parsed_units:
        return _report(errors, storyboard_sha256)
    body_end = parsed_units[-1][2]
    if not _close(parsed_units[0][1], 0.0):
        _error(errors, "timeline", "timeline must start at zero")

    for origin, occurrences in origins.items():
        ordered = sorted(occurrences)
        for previous, current in zip(ordered, ordered[1:]):
            if current[0] > previous[1] + TIME_TOLERANCE:
                _error(errors, "evidence_origin", f"evidence origin is reused across non-contiguous units: {origin}")
                break

    credits = storyboard.get("credit_units")
    total_end = body_end
    if not isinstance(credits, list) or not credits:
        _error(errors, "credits_timeline", "credits must be non-empty and extend from body end to total duration")
    else:
        credit_cursor = body_end
        for index, credit in enumerate(credits):
            interval = _timeline(credit) if isinstance(credit, dict) else None
            if interval is None:
                _error(errors, "credits_timeline", f"credits timeline is invalid at index {index}")
                continue
            start, end = interval
            if not _close(start, credit_cursor) or end <= start or credit.get("semantic_status") != "credits":
                _error(errors, "credits_timeline", f"credits must be positive and contiguous at index {index}")
            credit_cursor = end
        total_end = credit_cursor

    if exact_five_seconds / len(units) > FIXED_FIVE_SECOND_SHARE_LIMIT:
        _error(errors, "five_second_wall", "fixed five-second wall exceeds the allowed share of audience visual units")

    if body_end <= 0:
        _error(errors, "third_party_coverage", "third-party coverage denominator must be positive")
    elif isinstance(locked_policy, dict):
        minimum_third_party = _number(locked_policy.get("third_party_primary_min_ratio"))
        minimum_video = _number(locked_policy.get("third_party_internal_video_min_ratio"))
        third_party_ratio = third_party_seconds / body_end
        video_ratio = third_party_video_seconds / third_party_seconds if third_party_seconds > 0 else 0.0
        if minimum_third_party is not None and third_party_ratio + RATIO_TOLERANCE < minimum_third_party:
            _error(errors, "third_party_coverage", "third-party coverage is below the locked brief minimum")
        if minimum_video is not None and video_ratio + RATIO_TOLERANCE < minimum_video:
            _error(errors, "third_party_coverage", "third-party video coverage within third-party material is below the locked brief minimum")

    _validate_progress(storyboard, body_end, total_end, errors)
    return _report(errors, storyboard_sha256, {
        "audience_unit_count": len(units),
        "body_duration_seconds": body_end,
        "total_duration_seconds": total_end,
        "third_party_ratio": third_party_seconds / body_end if body_end > 0 else 0.0,
        "third_party_video_ratio": third_party_video_seconds / third_party_seconds if third_party_seconds > 0 else 0.0,
        "exact_five_second_unit_share": exact_five_seconds / len(units),
    })


def _report(errors: list[dict], storyboard_sha256: str | None, metrics: dict | None = None) -> dict:
    return {
        "schema": SCHEMA,
        "status": "FAIL" if errors else "PASS",
        "failed_checks": sorted({item["check"] for item in errors}),
        "findings": errors,
        "storyboard_sha256": storyboard_sha256,
        "metrics": metrics or {},
        "scope": "mechanical-only; does not replace independent G1 visual review",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--storyboard", required=True, type=Path)
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--locked-policy", type=Path)
    args = parser.parse_args()
    storyboard_path = args.storyboard.resolve()
    storyboard = json.loads(storyboard_path.read_text(encoding="utf-8"))
    policy = json.loads(args.locked_policy.read_text(encoding="utf-8")) if args.locked_policy else None
    report = validate_storyboard(
        storyboard,
        project=args.project,
        locked_policy=policy,
        storyboard_sha256=_sha256(storyboard_path),
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
