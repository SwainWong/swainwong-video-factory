#!/usr/bin/env python3
"""Validate paired short-phrase Chinese and English WebVTT subtitle authorities."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


TIMING = re.compile(r"^(\d{2}):(\d{2}):(\d{2})[.,](\d{3})\s+-->\s+(\d{2}):(\d{2}):(\d{2})[.,](\d{3})")


def _seconds(parts: tuple[str, str, str, str]) -> float:
    hour, minute, second, millis = map(int, parts)
    return hour * 3600 + minute * 60 + second + millis / 1000


def parse_vtt(text: str) -> list[dict[str, Any]]:
    lines = text.replace("\r\n", "\n").split("\n")
    cues: list[dict[str, Any]] = []
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if not line or line == "WEBVTT" or line.startswith("NOTE"):
            index += 1
            continue
        cue_id = line
        index += 1
        if index >= len(lines):
            break
        match = TIMING.match(lines[index].strip())
        if not match:
            index += 1
            continue
        start = _seconds(match.groups()[:4])
        end = _seconds(match.groups()[4:])
        index += 1
        content: list[str] = []
        while index < len(lines) and lines[index].strip():
            content.append(lines[index].strip())
            index += 1
        cues.append({"id": cue_id, "start": start, "end": end, "lines": content, "text": " ".join(content)})
    return cues


def _visible_zh_chars(text: str) -> int:
    return len(re.findall(r"[\u3400-\u9fffA-Za-z0-9]", text))


def _visible_en_chars(text: str) -> int:
    return len(re.sub(r"\s+", "", text))


def evaluate_vtt_pair(
    zh_text: str,
    en_text: str,
    *,
    max_duration: float = 4.5,
    max_zh_chars: int = 20,
    max_en_chars: int = 56,
    max_zh_cps: float = 12.0,
    max_en_cps: float = 24.0,
) -> dict[str, Any]:
    zh = parse_vtt(zh_text)
    en = parse_vtt(en_text)
    findings: list[dict[str, Any]] = []
    if not zh or not en:
        findings.append({"code": "NO_CUES", "message": "both language authorities must contain cues"})
    if len(zh) != len(en):
        findings.append({"code": "PAIR_COUNT_MISMATCH", "message": "Chinese and English cue counts differ", "zh": len(zh), "en": len(en)})

    durations: list[float] = []
    for index, (zh_cue, en_cue) in enumerate(zip(zh, en)):
        cue_id = zh_cue["id"]
        if cue_id != en_cue["id"]:
            findings.append({"code": "PAIR_ID_MISMATCH", "cue_index": index, "zh_id": cue_id, "en_id": en_cue["id"]})
        if abs(zh_cue["start"] - en_cue["start"]) > 0.001 or abs(zh_cue["end"] - en_cue["end"]) > 0.001:
            findings.append({"code": "PAIR_TIMING_MISMATCH", "cue_id": cue_id, "zh": [zh_cue["start"], zh_cue["end"]], "en": [en_cue["start"], en_cue["end"]]})
        duration = zh_cue["end"] - zh_cue["start"]
        durations.append(duration)
        if duration <= 0:
            findings.append({"code": "INVALID_CUE_DURATION", "cue_id": cue_id, "duration": duration})
            continue
        if duration > max_duration:
            findings.append({"code": "CUE_TOO_LONG", "cue_id": cue_id, "actual": round(duration, 3), "maximum": max_duration})
        if len(zh_cue["lines"]) != 1 or len(en_cue["lines"]) != 1:
            findings.append({"code": "LANGUAGE_LINE_COUNT", "cue_id": cue_id, "message": "each language authority must contribute exactly one line to the bilingual block"})
        zh_chars = _visible_zh_chars(zh_cue["text"])
        en_chars = _visible_en_chars(en_cue["text"])
        if zh_chars > max_zh_chars:
            findings.append({"code": "ZH_TOO_MANY_CHARS", "cue_id": cue_id, "actual": zh_chars, "maximum": max_zh_chars})
        if en_chars > max_en_chars:
            findings.append({"code": "EN_TOO_MANY_CHARS", "cue_id": cue_id, "actual": en_chars, "maximum": max_en_chars})
        if zh_chars / duration > max_zh_cps:
            findings.append({"code": "ZH_READING_SPEED", "cue_id": cue_id, "actual": round(zh_chars / duration, 2), "maximum": max_zh_cps})
        if en_chars / duration > max_en_cps:
            findings.append({"code": "EN_READING_SPEED", "cue_id": cue_id, "actual": round(en_chars / duration, 2), "maximum": max_en_cps})

    return {
        "schema": "swainwong.subtitle-phrase-gate.v1",
        "status": "PASS" if not findings else "REVISE",
        "metrics": {
            "cue_count": len(zh),
            "average_duration": round(sum(durations) / len(durations), 3) if durations else None,
            "maximum_duration": round(max(durations), 3) if durations else None,
        },
        "policy": {
            "max_duration": max_duration,
            "max_zh_chars": max_zh_chars,
            "max_en_chars": max_en_chars,
            "max_zh_cps": max_zh_cps,
            "max_en_cps": max_en_cps,
            "one_bilingual_block_per_cue": True,
        },
        "findings": findings,
        "final_pixel_review_required": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zh-vtt", type=Path, required=True)
    parser.add_argument("--en-vtt", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--max-duration", type=float, default=4.5)
    parser.add_argument("--max-zh-chars", type=int, default=20)
    parser.add_argument("--max-en-chars", type=int, default=56)
    parser.add_argument("--max-zh-cps", type=float, default=12.0)
    parser.add_argument("--max-en-cps", type=float, default=24.0)
    args = parser.parse_args()
    report = evaluate_vtt_pair(
        args.zh_vtt.read_text(encoding="utf-8"),
        args.en_vtt.read_text(encoding="utf-8"),
        max_duration=args.max_duration,
        max_zh_chars=args.max_zh_chars,
        max_en_chars=args.max_en_chars,
        max_zh_cps=args.max_zh_cps,
        max_en_cps=args.max_en_cps,
    )
    report["inputs"] = {
        "zh_vtt": {"path": str(args.zh_vtt.resolve()), "sha256": hashlib.sha256(args.zh_vtt.read_bytes()).hexdigest()},
        "en_vtt": {"path": str(args.en_vtt.resolve()), "sha256": hashlib.sha256(args.en_vtt.read_bytes()).hexdigest()},
    }
    output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(output, encoding="utf-8")
    print(output, end="")
    raise SystemExit(0 if report["status"] == "PASS" else 2)


if __name__ == "__main__":
    main()
