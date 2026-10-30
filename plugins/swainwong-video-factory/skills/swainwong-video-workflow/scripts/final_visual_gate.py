#!/usr/bin/env python3
"""Deterministic final-pixel contract checks for chapter navigation and third-party footage."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
from typing import Any


INPUT_SCHEMA = "swainwong.final-visual-gate-input.v2"
OUTPUT_SCHEMA = "swainwong.final-visual-gate.v2"
FULL_FRAME_MODES = {
    "cover_full_frame",
    "cover_crop_16_9_full_frame_no_matte",
    "focus_crop_16_9_full_frame_no_matte",
}
FOREGROUND_MODES = {"blurred_background_with_clear_foreground"}
MAX_PIXEL_TOLERANCE = 3.0
MAX_FULL_FRAME_LINEAR_UPSCALE = 1.5
MAX_FOREGROUND_LINEAR_UPSCALE = 1.5
MINIMUM_READABLE_TEXT_SECONDS = 1.5
MINIMUM_VIDEO_BITS_PER_PIXEL_FRAME = 0.006
MINIMUM_SUBTITLE_PIXEL_PROOFS = 3
REQUIRED_LOGO_ANCHOR = "lower-right"
FORBIDDEN_PRIMARY_TYPES = {
    "svg",
    "code-vector",
    "code-vector-as-primary-content",
    "generic-vector-illustration",
    "large-placeholder-infographic",
    "vector-static",
}
IMPLIED_READABLE_TYPES = {
    "typographic-page",
    "editable-page",
    "data-card",
    "credit-page",
    "code-vector",
    "code-vector-as-primary-content",
    "large-placeholder-infographic",
    "vector-static",
}
ALLOWED_SEMANTIC_STATUSES = {
    "direct_evidence",
    "contextual",
    "illustrative_only",
    "original_explanation",
    "credits",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _rate(value: str | None) -> float:
    if not value or value == "0/0":
        return 0.0
    numerator, separator, denominator = value.partition("/")
    if separator:
        return float(numerator) / float(denominator)
    return float(value)


def _probe_video(path_value: str) -> dict:
    path = Path(path_value).resolve()
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"video source is missing or not a regular file: {path}")
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "format=duration,bit_rate:stream=width,height,bit_rate,avg_frame_rate", "-of", "json", str(path)],
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    value = json.loads(probe.stdout)
    streams = value.get("streams") or []
    if not streams:
        raise ValueError(f"video source has no video stream: {path}")
    stream = streams[0]
    bit_rate = stream.get("bit_rate") or value.get("format", {}).get("bit_rate") or 0
    return {
        "path": str(path),
        "sha256": _sha256(path),
        "duration_seconds": float(value.get("format", {}).get("duration") or 0),
        "width": int(stream.get("width") or 0),
        "height": int(stream.get("height") or 0),
        "bit_rate": int(bit_rate),
        "frame_rate": _rate(stream.get("avg_frame_rate")),
    }


def _normalized_type(value: str) -> str:
    return value.strip().lower().replace("_", "-").replace(" ", "-")


def _nonempty_text_or_mapping(value: Any) -> bool:
    """Accept concise text or a structured locator/date object with real content."""
    if isinstance(value, str):
        return bool(value.strip())
    if not isinstance(value, dict) or not value:
        return False
    if not all(isinstance(key, str) and key.strip() for key in value):
        return False

    def meaningful(item: Any) -> bool:
        if isinstance(item, str):
            return bool(item.strip())
        if isinstance(item, dict):
            return bool(item) and any(meaningful(child) for child in item.values())
        if isinstance(item, list):
            return bool(item) and any(meaningful(child) for child in item)
        return item is not None

    return any(meaningful(item) for item in value.values())


def _required_navigation_times(chapters: list[dict], duration: float) -> list[float]:
    times = {0.0, duration}
    for chapter in chapters:
        start = float(chapter["start_seconds"])
        end = float(chapter["end_seconds"])
        times.add((start + end) / 2)
    for chapter in chapters[:-1]:
        boundary = float(chapter["end_seconds"])
        times.update({max(0.0, boundary - 0.1), boundary, min(duration, boundary + 0.1)})
    return sorted(times)


def _extract_top_frame(path: str, time_seconds: float, width: int, bar_height: int) -> bytes:
    result = subprocess.run(
        [
            "ffmpeg", "-v", "error", "-i", path, "-ss", f"{time_seconds:.6f}",
            "-frames:v", "1", "-vf", f"crop={width}:{bar_height}:0:0",
            "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1",
        ],
        check=True,
        capture_output=True,
        timeout=60,
    )
    expected = width * bar_height * 3
    if len(result.stdout) != expected:
        raise ValueError(f"could not extract final navigation pixels at {time_seconds:.3f}s")
    return result.stdout


def _extract_frame_image(path: str, time_seconds: float | None = None):
    try:
        import cv2
        import numpy as np
    except ImportError as exc:
        raise ValueError("final visual source-presence gate requires OpenCV and NumPy") from exc
    command = ["ffmpeg", "-v", "error", "-i", path]
    if time_seconds is not None:
        command.extend(["-ss", f"{time_seconds:.6f}"])
    command.extend(["-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "pipe:1"])
    result = subprocess.run(command, check=True, capture_output=True, timeout=60)
    image = cv2.imdecode(np.frombuffer(result.stdout, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"could not decode visual source frame: {path}")
    return image


def _appearance_similarity(source, candidate) -> dict:
    import cv2
    import numpy as np

    def bounded(image):
        height, width = image.shape[:2]
        scale = min(1.0, 960.0 / max(width, height))
        return cv2.resize(image, (max(1, round(width * scale)), max(1, round(height * scale))))

    source = bounded(source)
    candidate = bounded(candidate)
    gray_source = cv2.cvtColor(source, cv2.COLOR_BGR2GRAY)
    gray_candidate = cv2.cvtColor(candidate, cv2.COLOR_BGR2GRAY)
    orb = cv2.ORB_create(nfeatures=1800)
    source_keypoints, source_descriptors = orb.detectAndCompute(gray_source, None)
    candidate_keypoints, candidate_descriptors = orb.detectAndCompute(gray_candidate, None)
    good_matches = 0
    if source_descriptors is not None and candidate_descriptors is not None:
        matcher = cv2.BFMatcher(cv2.NORM_HAMMING)
        for pair in matcher.knnMatch(source_descriptors, candidate_descriptors, k=2):
            if len(pair) == 2 and pair[0].distance < 0.75 * pair[1].distance:
                good_matches += 1
    hsv_source = cv2.cvtColor(source, cv2.COLOR_BGR2HSV)
    hsv_candidate = cv2.cvtColor(candidate, cv2.COLOR_BGR2HSV)
    source_hist = cv2.normalize(cv2.calcHist([hsv_source], [0, 1], None, [32, 32], [0, 180, 0, 256]), None).flatten()
    candidate_hist = cv2.normalize(cv2.calcHist([hsv_candidate], [0, 1], None, [32, 32], [0, 180, 0, 256]), None).flatten()
    histogram_correlation = float(cv2.compareHist(source_hist, candidate_hist, cv2.HISTCMP_CORREL))
    source_mean = np.array(cv2.mean(source)[:3])
    candidate_mean = np.array(cv2.mean(candidate)[:3])
    mean_color_delta = float(np.linalg.norm(source_mean - candidate_mean))
    present = good_matches >= 12 or (histogram_correlation >= 0.92 and mean_color_delta <= 18.0)
    return {
        "present": present,
        "orb_good_matches": good_matches,
        "histogram_correlation": round(histogram_correlation, 6),
        "mean_color_delta": round(mean_color_delta, 6),
    }


def extract_source_appearance_facts(candidate_facts: dict, video_uses: list[dict], image_uses: list[dict]) -> dict:
    candidate_path = candidate_facts["path"]
    candidate_frame_interval = 1.0 / max(float(candidate_facts.get("frame_rate") or 30.0), 1.0)
    results = {}
    for use in video_uses:
        timeline_start = float(use["timeline_start"])
        timeline_end = float(use["timeline_end"])
        source_start = float(use["source_in"])
        source_end = float(use["source_out"])
        end_fraction = max(0.6, 0.9 - candidate_frame_interval / (timeline_end - timeline_start))
        fractions = (0.1, 0.5, end_fraction)
        samples = []
        for fraction in fractions:
            timeline_time = timeline_start + (timeline_end - timeline_start) * fraction
            source_time = source_start + (source_end - source_start) * fraction
            measurement = _appearance_similarity(
                _extract_frame_image(str(Path(use["source_path"]).resolve()), source_time),
                _extract_frame_image(candidate_path, timeline_time),
            )
            samples.append({"timeline_time": timeline_time, "source_time": source_time, **measurement})
        results[use["clip_id"]] = {"present": all(item["present"] for item in samples), "samples": samples}
    for use in image_uses:
        timeline_start = float(use["timeline_start"])
        timeline_end = float(use["timeline_end"])
        source_image = _extract_frame_image(str(Path(use["source_path"]).resolve()))
        samples = []
        end_fraction = max(0.6, 0.9 - candidate_frame_interval / (timeline_end - timeline_start))
        for fraction in (0.1, 0.5, end_fraction):
            timeline_time = timeline_start + (timeline_end - timeline_start) * fraction
            measurement = _appearance_similarity(source_image, _extract_frame_image(candidate_path, timeline_time))
            samples.append({"timeline_time": timeline_time, **measurement})
        results[use["clip_id"]] = {"present": all(item["present"] for item in samples), "samples": samples}
    return results


def extract_subtitle_pixel_facts(candidate_facts: dict, proofs: list[dict]) -> dict:
    """Compare final pixels with same-frame clean references to prove subtitle burn-in exists."""
    import cv2
    import numpy as np

    results = {}
    for index, proof in enumerate(proofs):
        cue_id = proof.get("cue_id")
        clean_path = Path(str(proof.get("clean_reference_path", ""))).resolve()
        if not clean_path.is_file() or clean_path.is_symlink():
            raise ValueError(f"subtitle_pixel_proofs[{index}] clean reference is missing or not a regular file: {clean_path}")
        if proof.get("clean_reference_sha256") != _sha256(clean_path):
            raise ValueError(f"subtitle_pixel_proofs[{index}] clean reference sha256 mismatch")
        time_seconds = _finite_number(proof.get("time_seconds"), f"subtitle_pixel_proofs[{index}].time_seconds")
        candidate_frame = _extract_frame_image(candidate_facts["path"], time_seconds)
        clean_frame = _extract_frame_image(str(clean_path), proof.get("clean_reference_time_seconds"))
        if candidate_frame.shape[:2] != clean_frame.shape[:2]:
            raise ValueError(f"subtitle_pixel_proofs[{index}] clean reference dimensions do not match candidate")
        region = proof.get("region")
        if not isinstance(region, dict):
            raise ValueError(f"subtitle_pixel_proofs[{index}].region must be an object")
        x = int(_finite_number(region.get("x"), f"subtitle_pixel_proofs[{index}].region.x"))
        y = int(_finite_number(region.get("y"), f"subtitle_pixel_proofs[{index}].region.y"))
        width = int(_finite_number(region.get("width"), f"subtitle_pixel_proofs[{index}].region.width", positive=True))
        height = int(_finite_number(region.get("height"), f"subtitle_pixel_proofs[{index}].region.height", positive=True))
        frame_height, frame_width = candidate_frame.shape[:2]
        if x < 0 or y < 0 or x + width > frame_width or y + height > frame_height:
            raise ValueError(f"subtitle_pixel_proofs[{index}].region is outside candidate frame")
        candidate_roi = candidate_frame[y:y + height, x:x + width]
        clean_roi = clean_frame[y:y + height, x:x + width]
        delta = cv2.absdiff(candidate_roi, clean_roi)
        mask = (np.max(delta, axis=2) >= 35).astype(np.uint8)
        changed_fraction = float(mask.mean())
        row_threshold = max(10, round(width * 0.005))
        active_rows = np.count_nonzero(mask, axis=1) >= row_threshold
        bands = []
        start = None
        last = None
        for row, active in enumerate(active_rows):
            if active:
                if start is None:
                    start = row
                last = row
            elif start is not None and last is not None and row - last > 3:
                if last - start + 1 >= 4:
                    bands.append([start, last])
                start = None
                last = None
        if start is not None and last is not None and last - start + 1 >= 4:
            bands.append([start, last])
        results[str(cue_id)] = {
            "present": changed_fraction >= 0.001 and bool(bands),
            "changed_fraction": round(changed_fraction, 6),
            "detected_line_bands": len(bands),
            "line_bands": bands,
        }
    return results


def _subtitle_pixel_check(manifest: dict, facts: dict, duration: float) -> dict:
    policy = manifest.get("subtitle_policy")
    proofs = manifest.get("subtitle_pixel_proofs")
    if not isinstance(policy, dict):
        raise ValueError("subtitle_policy must be an object")
    languages = policy.get("expected_languages")
    if not isinstance(languages, list) or not languages or not all(isinstance(item, str) and item for item in languages):
        raise ValueError("subtitle_policy.expected_languages must be a non-empty string list")
    if not isinstance(proofs, list):
        raise ValueError("subtitle_pixel_proofs must be a list")
    required = max(MINIMUM_SUBTITLE_PIXEL_PROOFS, int(policy.get("minimum_pixel_proofs") or 0))
    issues = []
    if len(proofs) < required:
        issues.append({"reason": "insufficient_pixel_proofs", "required": required, "actual": len(proofs)})
    cue_ids = set()
    bins = set()
    for index, proof in enumerate(proofs):
        if not isinstance(proof, dict):
            raise ValueError(f"subtitle_pixel_proofs[{index}] must be an object")
        cue_id = proof.get("cue_id")
        if not isinstance(cue_id, str) or not cue_id:
            raise ValueError(f"subtitle_pixel_proofs[{index}].cue_id is required")
        if cue_id in cue_ids:
            issues.append({"cue_id": cue_id, "reason": "duplicate_cue_id"})
        cue_ids.add(cue_id)
        time_seconds = _finite_number(proof.get("time_seconds"), f"subtitle_pixel_proofs[{index}].time_seconds")
        if time_seconds < 0 or time_seconds > duration:
            issues.append({"cue_id": cue_id, "reason": "cue_time_outside_candidate"})
        else:
            bins.add(min(2, int(time_seconds / max(duration, 1e-9) * 3)))
        region = proof.get("region")
        if not isinstance(region, dict) or not all(name in region for name in ("x", "y", "width", "height")):
            raise ValueError(f"subtitle_pixel_proofs[{index}].region requires x, y, width and height")
        measurement = facts.get(cue_id)
        if not isinstance(measurement, dict) or measurement.get("present") is not True:
            issues.append({"cue_id": cue_id, "reason": "subtitle_pixels_not_detected", "measurement": measurement})
            continue
        detected_bands = int(measurement.get("detected_line_bands") or 0)
        if detected_bands < len(languages):
            issues.append({"cue_id": cue_id, "reason": "fewer_subtitle_line_bands_than_languages", "expected": len(languages), "actual": detected_bands})
    if len(proofs) >= required and bins != {0, 1, 2}:
        issues.append({"reason": "proofs_do_not_cover_beginning_middle_end", "covered_bins": sorted(bins)})
    return {"status": "PASS" if not issues else "FAIL", "issues": issues, "measurements": facts, "expected_languages": languages}


def extract_navigation_pixel_facts(candidate_facts: dict, chapters: list[dict]) -> dict:
    path = candidate_facts["path"]
    width = int(candidate_facts["width"])
    height = int(candidate_facts["height"])
    duration = float(candidate_facts["duration_seconds"])
    bar_height = min(height, max(8, round(height * 70 / 1080)))
    fill_height = max(2, round(bar_height * 8 / 70))
    times = _required_navigation_times(chapters, duration)
    frame_rate = float(candidate_facts.get("frame_rate") or 30.0)
    last_frame_time = max(0.0, duration - 1.0 / max(frame_rate, 1.0))
    samples = []
    reference = None
    for time_seconds in times:
        frame = _extract_top_frame(path, min(time_seconds, last_frame_time), width, bar_height)
        if reference is None:
            reference = frame
        columns = []
        for x in range(width):
            hits = 0
            for y in range(fill_height):
                offset = (y * width + x) * 3
                red, green, blue = frame[offset:offset + 3]
                if red >= 100 and blue >= 65 and red >= green * 1.3 and blue >= green * 1.3:
                    hits += 1
            if hits >= max(1, fill_height // 3):
                columns.append(x)
        fill_x = float(max(columns) + 1) if columns else 0.0
        samples.append({"time_seconds": time_seconds, "fill_x": fill_x})

    label_top = min(bar_height - 1, fill_height + 1)
    label_bottom = bar_height
    label_visibility = []
    for chapter in chapters:
        start_x = max(0, min(width, round(width * float(chapter["start_seconds"]) / duration)))
        end_x = max(start_x + 1, min(width, round(width * float(chapter["end_seconds"]) / duration)))
        bright = 0
        for y in range(label_top, label_bottom):
            for x in range(start_x + 1, max(start_x + 1, end_x - 1)):
                offset = (y * width + x) * 3
                red, green, blue = reference[offset:offset + 3]
                if min(red, green, blue) >= 135 and max(red, green, blue) - min(red, green, blue) <= 55:
                    bright += 1
        area = max(1, (end_x - start_x) * max(1, label_bottom - label_top))
        label_visibility.append({"label": chapter["label"], "visible": bright >= max(1, round(area * 0.003)), "bright_pixels": bright})

    separators = []
    for chapter in chapters[:-1]:
        expected_x = round(width * float(chapter["end_seconds"]) / duration)
        best = 0
        best_x = expected_x
        for x in range(max(0, expected_x - 2), min(width, expected_x + 3)):
            bright = 0
            for y in range(label_top, label_bottom):
                offset = (y * width + x) * 3
                red, green, blue = reference[offset:offset + 3]
                if min(red, green, blue) >= 110 and max(red, green, blue) - min(red, green, blue) <= 70:
                    bright += 1
            if bright > best:
                best, best_x = bright, x
        visible = best >= max(1, round((label_bottom - label_top) * 0.45))
        separators.append({"expected_x": expected_x, "actual_x": best_x, "visible": visible, "bright_pixels": best})
    return {
        "bar_height": bar_height,
        "fill_height": fill_height,
        "samples": samples,
        "labels": label_visibility,
        "separators": separators,
    }


def _finite_number(value: Any, name: str, *, positive: bool = False) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    number = float(value)
    if positive and number <= 0:
        raise ValueError(f"{name} must be positive")
    return number


def _navigation_checks(manifest: dict, pixel_facts: dict) -> tuple[dict, dict]:
    candidate = manifest.get("candidate")
    if not isinstance(candidate, dict):
        raise ValueError("candidate must be an object")
    duration = _finite_number(candidate.get("duration_seconds"), "candidate.duration_seconds", positive=True)
    width = _finite_number(candidate.get("width"), "candidate.width", positive=True)

    navigation = manifest.get("chapter_navigation")
    if not isinstance(navigation, dict):
        raise ValueError("chapter_navigation must be an object")
    chapters = navigation.get("chapters")
    if not isinstance(chapters, list) or len(chapters) < 2:
        raise ValueError("chapter_navigation.chapters must contain at least two chapters")
    requested_tolerance = _finite_number(navigation.get("pixel_tolerance", 2.0), "chapter_navigation.pixel_tolerance")
    tolerance = min(requested_tolerance, MAX_PIXEL_TOLERANCE)
    if tolerance < 0:
        raise ValueError("chapter_navigation.pixel_tolerance must be non-negative")

    geometry_issues = []
    labels = []
    cursor_time = 0.0
    cursor_x = 0.0
    for index, chapter in enumerate(chapters):
        if not isinstance(chapter, dict):
            raise ValueError(f"chapter_navigation.chapters[{index}] must be an object")
        label = chapter.get("label")
        if not isinstance(label, str) or not label.strip():
            geometry_issues.append({"chapter": index, "reason": "missing_label"})
            label = ""
        labels.append(label.strip())
        start = _finite_number(chapter.get("start_seconds"), f"chapters[{index}].start_seconds")
        end = _finite_number(chapter.get("end_seconds"), f"chapters[{index}].end_seconds")
        start_x = _finite_number(chapter.get("rendered_start_x"), f"chapters[{index}].rendered_start_x")
        end_x = _finite_number(chapter.get("rendered_end_x"), f"chapters[{index}].rendered_end_x")
        expected_start_x = width * start / duration
        expected_end_x = width * end / duration
        if end <= start:
            geometry_issues.append({"chapter": index, "reason": "non_positive_duration"})
        if abs(start - cursor_time) > 0.01:
            geometry_issues.append({"chapter": index, "reason": "time_gap_or_overlap", "expected": cursor_time, "actual": start})
        if abs(start_x - cursor_x) > tolerance:
            geometry_issues.append({"chapter": index, "reason": "rendered_x_gap_or_overlap", "expected": cursor_x, "actual": start_x})
        if abs(start_x - expected_start_x) > tolerance or abs(end_x - expected_end_x) > tolerance:
            geometry_issues.append({
                "chapter": index,
                "reason": "width_not_duration_proportional",
                "expected": [expected_start_x, expected_end_x],
                "actual": [start_x, end_x],
            })
        cursor_time = end
        cursor_x = end_x
    if abs(cursor_time - duration) > 0.01:
        geometry_issues.append({"reason": "chapters_do_not_cover_candidate", "expected": duration, "actual": cursor_time})
    if abs(cursor_x - width) > tolerance:
        geometry_issues.append({"reason": "chapters_do_not_cover_frame_width", "expected": width, "actual": cursor_x})

    structure_issues = list(geometry_issues)
    if requested_tolerance > MAX_PIXEL_TOLERANCE:
        structure_issues.append({"reason": "pixel_tolerance_exceeds_plugin_limit", "limit": MAX_PIXEL_TOLERANCE, "actual": requested_tolerance})
    if navigation.get("track") != "single-full-width-segmented-navigation":
        structure_issues.append({"reason": "wrong_track_contract", "actual": navigation.get("track")})
    visible_labels = [item.get("label") for item in pixel_facts.get("labels", []) if item.get("visible") is True]
    visible_separators = [item for item in pixel_facts.get("separators", []) if item.get("visible") is True]
    if visible_labels != labels:
        structure_issues.append({"reason": "rendered_labels_not_visible_in_final_pixels", "expected": labels, "actual": visible_labels})
    if len(visible_separators) != len(chapters) - 1:
        structure_issues.append({"reason": "rendered_separators_not_visible_in_final_pixels", "expected": len(chapters) - 1, "actual": len(visible_separators)})

    samples = pixel_facts.get("samples")
    pixel_issues = []
    if not isinstance(samples, list) or not samples:
        pixel_issues.append({"reason": "final_pixel_samples_missing"})
        samples = []
    sample_times = []
    previous_time = -math.inf
    previous_fill = -math.inf
    for index, sample in enumerate(samples):
        if not isinstance(sample, dict):
            pixel_issues.append({"sample": index, "reason": "invalid_sample"})
            continue
        time = _finite_number(sample.get("time_seconds"), f"pixel_samples[{index}].time_seconds")
        fill = _finite_number(sample.get("fill_x"), f"pixel_samples[{index}].fill_x")
        expected = width * min(max(time, 0.0), duration) / duration
        sample_times.append(time)
        if time < previous_time - 0.001:
            pixel_issues.append({"sample": index, "reason": "time_not_monotonic"})
        if fill < previous_fill - tolerance:
            pixel_issues.append({"sample": index, "reason": "fill_not_monotonic", "previous": previous_fill, "actual": fill})
        if abs(fill - expected) > tolerance:
            pixel_issues.append({"sample": index, "reason": "fill_not_linear_to_real_time", "expected": expected, "actual": fill})
        previous_time = time
        previous_fill = fill
    required_times = [0.0, duration]
    for chapter in chapters[:-1]:
        boundary = float(chapter["end_seconds"])
        required_times.extend([max(0.0, boundary - 0.1), boundary, min(duration, boundary + 0.1)])
    for chapter in chapters:
        required_times.append((float(chapter["start_seconds"]) + float(chapter["end_seconds"])) / 2)
    missing_times = [required for required in required_times if not any(abs(actual - required) <= 0.011 for actual in sample_times)]
    if missing_times:
        pixel_issues.append({"reason": "chapter_boundary_pixel_samples_missing", "times": missing_times})

    structure = {"status": "PASS" if not structure_issues else "FAIL", "issues": structure_issues}
    pixels = {"status": "PASS" if not pixel_issues else "FAIL", "issues": pixel_issues, "sample_count": len(samples), "extracted": pixel_facts}
    return structure, pixels


def _origin_uniqueness(uses: list[dict]) -> dict:
    by_origin: dict[str, list[tuple[float, float, float, float, str]]] = {}
    identities: dict[str, set[str]] = {}
    for index, use in enumerate(uses):
        if not isinstance(use, dict):
            raise ValueError(f"third_party_video_uses[{index}] must be an object")
        origin = use.get("origin_id")
        clip_id = use.get("clip_id")
        if not isinstance(origin, str) or not origin.strip():
            raise ValueError(f"third_party_video_uses[{index}].origin_id is required")
        if not isinstance(clip_id, str) or not clip_id.strip():
            raise ValueError(f"third_party_video_uses[{index}].clip_id is required")
        start = _finite_number(use.get("timeline_start"), f"third_party_video_uses[{index}].timeline_start")
        end = _finite_number(use.get("timeline_end"), f"third_party_video_uses[{index}].timeline_end")
        source_in = _finite_number(use.get("source_in"), f"third_party_video_uses[{index}].source_in")
        source_out = _finite_number(use.get("source_out"), f"third_party_video_uses[{index}].source_out")
        if end <= start:
            raise ValueError(f"third_party_video_uses[{index}] has non-positive duration")
        if source_out <= source_in:
            raise ValueError(f"third_party_video_uses[{index}] has non-positive source duration")
        source_identity = use.get("source_sha256") or f"path:{Path(use.get('source_path', '')).resolve()}"
        identities.setdefault(source_identity, set()).add(origin)
        by_origin.setdefault(origin, []).append((start, end, source_in, source_out, clip_id))

    results = {}
    for origin, intervals in by_origin.items():
        intervals.sort()
        segments = []
        source_continuity_issues = []
        for start, end, source_in, source_out, clip_id in intervals:
            if not segments or start > segments[-1][1] + 0.01:
                segments.append([start, end, source_in, source_out, [clip_id]])
            else:
                if abs(source_in - segments[-1][3]) > 0.05:
                    source_continuity_issues.append({"previous_source_out": segments[-1][3], "next_source_in": source_in, "clip_id": clip_id})
                segments[-1][1] = max(segments[-1][1], end)
                segments[-1][3] = max(segments[-1][3], source_out)
                segments[-1][4].append(clip_id)
        results[origin] = {
            "status": "PASS" if len(segments) == 1 and not source_continuity_issues else "FAIL",
            "continuous_segments": len(segments),
            "segments": [
                {"start_seconds": item[0], "end_seconds": item[1], "source_in": item[2], "source_out": item[3], "clip_ids": item[4]}
                for item in segments
            ],
            "source_continuity_issues": source_continuity_issues,
        }
    conflicts = [
        {"source_identity": identity, "origin_ids": sorted(origins)}
        for identity, origins in identities.items()
        if len(origins) > 1
    ]
    results["__source_identity__"] = {"status": "PASS" if not conflicts else "FAIL", "conflicts": conflicts}
    return results


def _source_quality(uses: list[dict], source_facts: dict[str, dict]) -> dict:
    offenders = []
    measurements = []
    for index, use in enumerate(uses):
        source_path = str(Path(use.get("source_path", "")).resolve())
        facts = source_facts.get(source_path) or source_facts.get(use.get("source_path"))
        if not isinstance(facts, dict):
            raise ValueError(f"source media facts missing: {source_path}")
        source_width = _finite_number(facts.get("width"), f"source_facts[{source_path}].width", positive=True)
        source_height = _finite_number(facts.get("height"), f"source_facts[{source_path}].height", positive=True)
        if use.get("source_width") != source_width or use.get("source_height") != source_height:
            raise ValueError(f"source dimensions do not match trusted media probe: {source_path}")
        if use.get("source_sha256") != facts.get("sha256"):
            raise ValueError(f"source sha256 does not match trusted media probe: {source_path}")
        render_width = _finite_number(use.get("render_width"), f"third_party_video_uses[{index}].render_width", positive=True)
        render_height = _finite_number(use.get("render_height"), f"third_party_video_uses[{index}].render_height", positive=True)
        zoom = _finite_number(use.get("zoom", 1.0), f"third_party_video_uses[{index}].zoom", positive=True)
        bit_rate = _finite_number(facts.get("bit_rate"), f"source_facts[{source_path}].bit_rate", positive=True)
        frame_rate = _finite_number(facts.get("frame_rate"), f"source_facts[{source_path}].frame_rate", positive=True)
        bits_per_pixel_frame = bit_rate / (source_width * source_height * frame_rate)
        mode = use.get("composition_mode")
        if mode in FULL_FRAME_MODES:
            scale = max(render_width / source_width, render_height / source_height) * zoom
            limit = MAX_FULL_FRAME_LINEAR_UPSCALE
        elif mode in FOREGROUND_MODES:
            scale = min(render_width / source_width, render_height / source_height) * zoom
            limit = MAX_FOREGROUND_LINEAR_UPSCALE
        else:
            raise ValueError(f"unsupported composition_mode for source-quality gate: {mode}")
        measurement = {
            "clip_id": use["clip_id"],
            "origin_id": use["origin_id"],
            "composition_mode": mode,
            "linear_upscale": round(scale, 6),
            "limit": limit,
            "source_dimensions": [source_width, source_height],
            "render_dimensions": [render_width, render_height],
            "zoom": zoom,
            "bit_rate": bit_rate,
            "frame_rate": frame_rate,
            "bits_per_pixel_frame": round(bits_per_pixel_frame, 9),
            "minimum_bits_per_pixel_frame": MINIMUM_VIDEO_BITS_PER_PIXEL_FRAME,
        }
        measurements.append(measurement)
        if scale > limit + 1e-9 or bits_per_pixel_frame < MINIMUM_VIDEO_BITS_PER_PIXEL_FRAME:
            offenders.append(measurement)
    return {"status": "PASS" if not offenders else "FAIL", "offenders": offenders, "measurements": measurements}


def _audience_visual_checks(manifest: dict, duration: float) -> tuple[dict, dict, dict, dict, dict]:
    units = manifest.get("audience_visual_units")
    overlay = manifest.get("brand_overlay")
    if not isinstance(units, list) or not units:
        raise ValueError("audience_visual_units must be a non-empty list")
    forbidden_offenders = []
    duration_offenders = []
    coverage_issues = []
    semantic_issues = []
    evidence_overlay_origins: dict[str, list[str]] = {}
    cursor = 0.0
    ordered_units = sorted(units, key=lambda item: item.get("start_seconds", math.inf) if isinstance(item, dict) else math.inf)
    for index, unit in enumerate(ordered_units):
        if not isinstance(unit, dict):
            raise ValueError(f"audience_visual_units[{index}] must be an object")
        unit_id = unit.get("unit_id")
        primary_type = unit.get("primary_type")
        if not isinstance(unit_id, str) or not unit_id or not isinstance(primary_type, str) or not primary_type:
            raise ValueError(f"audience_visual_units[{index}] requires unit_id and primary_type")
        start = _finite_number(unit.get("start_seconds"), f"audience_visual_units[{index}].start_seconds")
        end = _finite_number(unit.get("end_seconds"), f"audience_visual_units[{index}].end_seconds")
        if end <= start:
            raise ValueError(f"audience_visual_units[{index}] has non-positive duration")
        normalized_type = _normalized_type(primary_type)
        sentence_ids = unit.get("sentence_ids")
        claim_ids = unit.get("claim_ids")
        fact_source_ids = unit.get("fact_source_ids")
        event_date_scope = unit.get("event_date_scope")
        semantic_status = unit.get("semantic_status")
        evidence_overlay_origin_ids = unit.get("evidence_overlay_origin_ids", [])
        visible_evidence = unit.get("visible_evidence", [])
        if not isinstance(sentence_ids, list) or not sentence_ids or not all(isinstance(item, str) and item for item in sentence_ids):
            semantic_issues.append({"unit_id": unit_id, "reason": "sentence_ids_missing"})
        if not isinstance(claim_ids, list) or not all(isinstance(item, str) and item for item in claim_ids):
            semantic_issues.append({"unit_id": unit_id, "reason": "claim_ids_invalid"})
        if not isinstance(fact_source_ids, list) or not all(isinstance(item, str) and item for item in fact_source_ids):
            semantic_issues.append({"unit_id": unit_id, "reason": "fact_source_ids_invalid"})
        valid_event_scope = (
            isinstance(event_date_scope, str) and bool(event_date_scope.strip())
        ) or (
            isinstance(event_date_scope, dict)
            and bool(event_date_scope)
            and all(isinstance(key, str) and key and isinstance(value, str) and value.strip() for key, value in event_date_scope.items())
        )
        if not valid_event_scope:
            semantic_issues.append({"unit_id": unit_id, "reason": "event_date_scope_missing"})
        if semantic_status not in ALLOWED_SEMANTIC_STATUSES:
            semantic_issues.append({"unit_id": unit_id, "reason": "semantic_status_invalid_or_direct_mismatch", "actual": semantic_status})
        if not isinstance(evidence_overlay_origin_ids, list) or not all(isinstance(item, str) and item for item in evidence_overlay_origin_ids):
            semantic_issues.append({"unit_id": unit_id, "reason": "evidence_overlay_origin_ids_invalid"})
            evidence_overlay_origin_ids = []
        for origin_id in evidence_overlay_origin_ids:
            evidence_overlay_origins.setdefault(origin_id, []).append(unit_id)
        if not isinstance(visible_evidence, list):
            semantic_issues.append({"unit_id": unit_id, "reason": "visible_evidence_must_be_a_list"})
            visible_evidence = []
        if semantic_status == "direct_evidence" and (not claim_ids or not fact_source_ids or not evidence_overlay_origin_ids or not visible_evidence):
            semantic_issues.append({"unit_id": unit_id, "reason": "direct_evidence_requires_claim_fact_source_visible_origin_and_locator_mapping"})
        if semantic_status in {"contextual", "illustrative_only", "original_explanation", "credits"} and visible_evidence:
            semantic_issues.append({"unit_id": unit_id, "reason": "non_direct_unit_must_not_claim_visible_evidence"})
        for evidence_index, item in enumerate(visible_evidence):
            if not isinstance(item, dict):
                semantic_issues.append({"unit_id": unit_id, "reason": "visible_evidence_row_must_be_object", "index": evidence_index})
                continue
            claim_id = item.get("claim_id")
            fact_source_id = item.get("fact_source_id")
            locator = item.get("locator_or_crop")
            evidence_date_scope = item.get("date_scope")
            interval_start = item.get("on_screen_start_seconds")
            interval_end = item.get("on_screen_end_seconds")
            if claim_id not in (claim_ids or []) or fact_source_id not in (fact_source_ids or []):
                semantic_issues.append({"unit_id": unit_id, "reason": "visible_evidence_claim_or_source_not_bound_to_unit", "index": evidence_index})
            if not _nonempty_text_or_mapping(locator) or not _nonempty_text_or_mapping(evidence_date_scope):
                semantic_issues.append({"unit_id": unit_id, "reason": "visible_evidence_locator_or_date_missing", "index": evidence_index})
            if not isinstance(interval_start, (int, float)) or not isinstance(interval_end, (int, float)) or interval_start < start or interval_end > end or interval_end <= interval_start:
                semantic_issues.append({"unit_id": unit_id, "reason": "visible_evidence_interval_invalid", "index": evidence_index, "unit_interval": [start, end], "actual": [interval_start, interval_end]})
        if normalized_type in FORBIDDEN_PRIMARY_TYPES:
            forbidden_offenders.append({"unit_id": unit_id, "primary_type": primary_type, "start_seconds": start, "end_seconds": end})
        readable = unit.get("contains_readable_text") is True or normalized_type in IMPLIED_READABLE_TYPES
        if readable and end - start + 1e-9 < MINIMUM_READABLE_TEXT_SECONDS:
            duration_offenders.append({
                "unit_id": unit_id,
                "duration_seconds": round(end - start, 6),
                "minimum_seconds": MINIMUM_READABLE_TEXT_SECONDS,
                "start_seconds": start,
                "end_seconds": end,
            })
        if abs(start - cursor) > 0.01:
            coverage_issues.append({"unit_id": unit_id, "reason": "gap_or_overlap", "expected_start": cursor, "actual_start": start})
        cursor = end
    if abs(cursor - duration) > 0.01:
        coverage_issues.append({"reason": "visual_units_do_not_cover_candidate", "expected_end": duration, "actual_end": cursor})
    for origin_id, unit_ids in evidence_overlay_origins.items():
        if len(unit_ids) > 1:
            semantic_issues.append({"reason": "evidence_overlay_origin_reused", "origin_id": origin_id, "unit_ids": unit_ids})
    if not isinstance(overlay, dict):
        raise ValueError("brand_overlay must be an object")
    required_anchor = REQUIRED_LOGO_ANCHOR
    overlay_issues = []
    if overlay.get("anchor") != required_anchor:
        overlay_issues.append({"reason": "wrong_anchor", "expected": required_anchor, "actual": overlay.get("anchor")})
    if overlay.get("transparent") is not True:
        overlay_issues.append({"reason": "logo_not_transparent"})
    if overlay.get("backing_plate") is not False:
        overlay_issues.append({"reason": "backing_plate_not_allowed"})
    return (
        {"status": "PASS" if not forbidden_offenders else "FAIL", "offenders": forbidden_offenders},
        {"status": "PASS" if not duration_offenders else "FAIL", "offenders": duration_offenders},
        {"status": "PASS" if not overlay_issues else "FAIL", "issues": overlay_issues},
        {"status": "PASS" if not coverage_issues else "FAIL", "issues": coverage_issues},
        {"status": "PASS" if not semantic_issues else "FAIL", "issues": semantic_issues},
    )


def _third_party_coverage_check(manifest: dict, duration: float) -> dict:
    policy = manifest.get("coverage_policy")
    if not isinstance(policy, dict):
        raise ValueError("coverage_policy must be an object")
    primary_min = _finite_number(policy.get("third_party_primary_min_ratio"), "coverage_policy.third_party_primary_min_ratio")
    video_min = _finite_number(policy.get("third_party_internal_video_min_ratio"), "coverage_policy.third_party_internal_video_min_ratio")
    if not 0 <= primary_min <= 1 or not 0 <= video_min <= 1:
        raise ValueError("coverage policy ratios must be between zero and one")
    third_party_seconds = 0.0
    third_party_video_seconds = 0.0
    for unit in manifest["audience_visual_units"]:
        primary_type = _normalized_type(str(unit.get("primary_type", "")))
        unit_duration = float(unit["end_seconds"]) - float(unit["start_seconds"])
        if primary_type in {"third-party-footage", "third-party-image"}:
            third_party_seconds += unit_duration
        if primary_type == "third-party-footage":
            third_party_video_seconds += unit_duration
    primary_ratio = third_party_seconds / duration
    video_ratio = third_party_video_seconds / third_party_seconds if third_party_seconds else 0.0
    issues = []
    if primary_ratio + 1e-9 < primary_min:
        issues.append({"reason": "third_party_primary_ratio_below_minimum", "actual": primary_ratio, "minimum": primary_min})
    if video_ratio + 1e-9 < video_min:
        issues.append({"reason": "third_party_internal_video_ratio_below_minimum", "actual": video_ratio, "minimum": video_min})
    return {
        "status": "PASS" if not issues else "FAIL",
        "third_party_seconds": round(third_party_seconds, 6),
        "third_party_video_seconds": round(third_party_video_seconds, 6),
        "third_party_primary_ratio": round(primary_ratio, 9),
        "third_party_internal_video_ratio": round(video_ratio, 9),
        "policy": {"third_party_primary_min_ratio": primary_min, "third_party_internal_video_min_ratio": video_min},
        "issues": issues,
    }


def _image_uniqueness(uses: list[dict]) -> dict:
    if not isinstance(uses, list):
        raise ValueError("third_party_image_uses must be a list")
    identities = {}
    origins = {}
    for index, use in enumerate(uses):
        if not isinstance(use, dict):
            raise ValueError(f"third_party_image_uses[{index}] must be an object")
        origin = use.get("origin_id")
        clip_id = use.get("clip_id")
        path = use.get("source_path")
        digest = use.get("source_sha256")
        if not all(isinstance(value, str) and value for value in (clip_id, origin, path, digest)):
            raise ValueError(f"third_party_image_uses[{index}] requires clip_id, origin_id, source_path and source_sha256")
        start = _finite_number(use.get("timeline_start"), f"third_party_image_uses[{index}].timeline_start")
        end = _finite_number(use.get("timeline_end"), f"third_party_image_uses[{index}].timeline_end")
        if end <= start:
            raise ValueError(f"third_party_image_uses[{index}] has non-positive duration")
        resolved = Path(path).resolve()
        if not resolved.is_file() or resolved.is_symlink():
            raise ValueError(f"image source is missing or not a regular file: {resolved}")
        actual_digest = _sha256(resolved)
        if digest != actual_digest:
            raise ValueError(f"image source sha256 does not match actual file: {resolved}")
        identities.setdefault(f"sha256:{actual_digest}", []).append(use.get("clip_id"))
        identities.setdefault(f"path:{resolved}", []).append(use.get("clip_id"))
        origins.setdefault(origin, []).append(use.get("clip_id"))
    offenders = {
        "source_identities": {key: value for key, value in identities.items() if len(value) > 1},
        "origins": {key: value for key, value in origins.items() if len(value) > 1},
    }
    passed = not offenders["source_identities"] and not offenders["origins"]
    return {"status": "PASS" if passed else "FAIL", "offenders": offenders, "count": len(uses)}


def validate_manifest(manifest: dict, *, candidate_facts: dict | None = None, source_facts: dict[str, dict] | None = None, pixel_facts: dict | None = None, appearance_facts: dict | None = None, subtitle_pixel_facts: dict | None = None, input_manifest_sha256: str | None = None) -> dict:
    if not isinstance(manifest, dict) or manifest.get("schema") != INPUT_SCHEMA:
        raise ValueError(f"manifest schema must be {INPUT_SCHEMA}")
    candidate = manifest.get("candidate")
    if not isinstance(candidate, dict):
        raise ValueError("candidate must be an object")
    candidate_path = candidate.get("path")
    if not isinstance(candidate_path, str) or not candidate_path:
        raise ValueError("candidate.path is required")
    candidate_facts = candidate_facts or _probe_video(candidate_path)
    if str(Path(candidate_path).resolve()) != str(Path(candidate_facts.get("path", "")).resolve()):
        raise ValueError("candidate path does not match trusted media probe")
    for name in ("sha256", "width", "height"):
        if candidate.get(name) != candidate_facts.get(name):
            raise ValueError(f"candidate {name} does not match trusted media probe")
    reported_duration = _finite_number(candidate.get("duration_seconds"), "candidate.duration_seconds", positive=True)
    actual_duration = _finite_number(candidate_facts.get("duration_seconds"), "candidate_facts.duration_seconds", positive=True)
    if abs(reported_duration - actual_duration) > 0.05:
        raise ValueError("candidate duration_seconds does not match trusted media probe")
    uses = manifest.get("third_party_video_uses")
    if not isinstance(uses, list) or not uses:
        raise ValueError("third_party_video_uses must be a non-empty list")
    if source_facts is None:
        source_facts = {}
        for use in uses:
            path = str(Path(use.get("source_path", "")).resolve())
            source_facts[path] = _probe_video(path)

    chapters = manifest.get("chapter_navigation", {}).get("chapters")
    if not isinstance(chapters, list):
        raise ValueError("chapter_navigation.chapters must be a list")
    pixel_facts = pixel_facts or extract_navigation_pixel_facts(candidate_facts, chapters)
    navigation_structure, navigation_pixels = _navigation_checks(manifest, pixel_facts)
    uniqueness = _origin_uniqueness(uses)
    uniqueness_status = "PASS" if all(item["status"] == "PASS" for item in uniqueness.values()) else "FAIL"
    source_quality = _source_quality(uses, source_facts)
    visual_asset_policy, readable_visual_duration, brand_overlay, visual_timeline_coverage, visual_semantic_contract = _audience_visual_checks(manifest, actual_duration)
    third_party_coverage = _third_party_coverage_check(manifest, actual_duration)
    subtitle_proofs = manifest.get("subtitle_pixel_proofs")
    if not isinstance(subtitle_proofs, list):
        raise ValueError("subtitle_pixel_proofs must be a list")
    subtitle_pixel_facts = subtitle_pixel_facts or extract_subtitle_pixel_facts(candidate_facts, subtitle_proofs)
    subtitle_pixel_presence = _subtitle_pixel_check(manifest, subtitle_pixel_facts, actual_duration)
    image_uses = manifest.get("third_party_image_uses", [])
    image_uniqueness = _image_uniqueness(image_uses)
    appearance_facts = appearance_facts or extract_source_appearance_facts(candidate_facts, uses, image_uses)
    missing_appearance = [use.get("clip_id") for use in [*uses, *image_uses] if not appearance_facts.get(use.get("clip_id"), {}).get("present")]
    source_appearance = {"status": "PASS" if not missing_appearance else "FAIL", "missing_clip_ids": missing_appearance, "measurements": appearance_facts}
    visual_units = {item.get("unit_id"): item for item in manifest["audience_visual_units"] if isinstance(item, dict)}
    footage_mapping_issues = []
    for use in uses:
        unit = visual_units.get(use.get("clip_id"))
        if not unit or _normalized_type(str(unit.get("primary_type", ""))) != "third-party-footage":
            footage_mapping_issues.append({"clip_id": use.get("clip_id"), "reason": "missing_matching_third_party_visual_unit"})
            continue
        if abs(float(unit.get("start_seconds")) - float(use.get("timeline_start"))) > 0.01 or abs(float(unit.get("end_seconds")) - float(use.get("timeline_end"))) > 0.01:
            footage_mapping_issues.append({"clip_id": use.get("clip_id"), "reason": "timeline_mismatch"})
    declared_footage_units = {key for key, unit in visual_units.items() if _normalized_type(str(unit.get("primary_type", ""))) == "third-party-footage"}
    undeclared_uses = declared_footage_units - {use.get("clip_id") for use in uses}
    for clip_id in sorted(undeclared_uses):
        footage_mapping_issues.append({"clip_id": clip_id, "reason": "third_party_visual_unit_missing_source_use"})
    footage_mapping = {"status": "PASS" if not footage_mapping_issues else "FAIL", "issues": footage_mapping_issues}
    image_mapping_issues = []
    for use in image_uses:
        unit = visual_units.get(use.get("clip_id"))
        if not unit or _normalized_type(str(unit.get("primary_type", ""))) != "third-party-image":
            image_mapping_issues.append({"clip_id": use.get("clip_id"), "reason": "missing_matching_third_party_image_visual_unit"})
            continue
        if abs(float(unit.get("start_seconds")) - float(use.get("timeline_start"))) > 0.01 or abs(float(unit.get("end_seconds")) - float(use.get("timeline_end"))) > 0.01:
            image_mapping_issues.append({"clip_id": use.get("clip_id"), "reason": "timeline_mismatch"})
    declared_image_units = {key for key, unit in visual_units.items() if _normalized_type(str(unit.get("primary_type", ""))) == "third-party-image"}
    for clip_id in sorted(declared_image_units - {use.get("clip_id") for use in image_uses}):
        image_mapping_issues.append({"clip_id": clip_id, "reason": "third_party_image_visual_unit_missing_source_use"})
    image_mapping = {"status": "PASS" if not image_mapping_issues else "FAIL", "issues": image_mapping_issues}
    summary = {
        "chapter_navigation_structure": navigation_structure,
        "chapter_navigation_pixel_progress": navigation_pixels,
        "third_party_origin_uniqueness": {"status": uniqueness_status},
        "source_quality": {"status": source_quality["status"]},
        "visual_asset_policy": {"status": visual_asset_policy["status"]},
        "readable_visual_duration": {"status": readable_visual_duration["status"]},
        "brand_overlay": {"status": brand_overlay["status"]},
        "visual_timeline_coverage": {"status": visual_timeline_coverage["status"]},
        "visual_semantic_contract": {"status": visual_semantic_contract["status"]},
        "third_party_coverage": {"status": third_party_coverage["status"]},
        "subtitle_pixel_presence": {"status": subtitle_pixel_presence["status"]},
        "third_party_image_uniqueness": {"status": image_uniqueness["status"]},
        "third_party_footage_mapping": {"status": footage_mapping["status"]},
        "third_party_image_mapping": {"status": image_mapping["status"]},
        "third_party_source_appearance": {"status": source_appearance["status"]},
    }
    failed = [name for name, result in summary.items() if result["status"] != "PASS"]
    return {
        "schema": OUTPUT_SCHEMA,
        "input_manifest_sha256": input_manifest_sha256,
        "candidate": manifest["candidate"],
        "status": "PASS" if not failed else "FAIL",
        "summary": summary,
        "failed_checks": failed,
        "checks": {
            "chapter_navigation_structure": navigation_structure,
            "chapter_navigation_pixel_progress": navigation_pixels,
            "third_party_origin_uniqueness": uniqueness,
            "source_quality": source_quality,
            "visual_asset_policy": visual_asset_policy,
            "readable_visual_duration": readable_visual_duration,
            "brand_overlay": brand_overlay,
            "visual_timeline_coverage": visual_timeline_coverage,
            "visual_semantic_contract": visual_semantic_contract,
            "third_party_coverage": third_party_coverage,
            "subtitle_pixel_presence": subtitle_pixel_presence,
            "third_party_image_uniqueness": image_uniqueness,
            "third_party_footage_mapping": footage_mapping,
            "third_party_image_mapping": image_mapping,
            "third_party_source_appearance": source_appearance,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    manifest_bytes = args.manifest.read_bytes()
    result = validate_manifest(
        json.loads(manifest_bytes),
        input_manifest_sha256=hashlib.sha256(manifest_bytes).hexdigest(),
    )
    rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    raise SystemExit(0 if result["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
