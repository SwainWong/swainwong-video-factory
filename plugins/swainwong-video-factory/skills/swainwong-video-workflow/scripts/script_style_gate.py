#!/usr/bin/env python3
"""Reject obvious thought-process narration before voice or storyboard production."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


META_PATTERNS = (
    ("clarify_before_start", re.compile(r"先把.{0,20}说清楚")),
    ("the_real_question", re.compile(r"真正的问题")),
    ("if_the_answer_were_only", re.compile(r"如果答案只是")),
    ("obviously_not_so_simple", re.compile(r"显然.{0,8}没这么简单")),
    ("eliminate_easy_answer", re.compile(r"先排除.{0,12}答案")),
    ("worth_asking_instead", re.compile(r"更值得追问")),
    ("defensive_attention", re.compile(r"注意[，,:：].{0,18}不等于")),
    ("numbered_layer", re.compile(r"第[一二三四五六七八九十]+层")),
    ("more_accurate_wording", re.compile(r"更准确的说法")),
    ("so_we_still_need_to", re.compile(r"所以.{0,10}还得")),
)


def _finding(code: str, message: str, **details: Any) -> dict[str, Any]:
    return {"code": code, "message": message, **details}


def evaluate_script(
    payload: dict[str, Any],
    *,
    min_cjk_chars: int | None = None,
    max_cjk_chars: int | None = None,
    max_meta_markers: int = 2,
    max_rhetorical_questions: int = 3,
) -> dict[str, Any]:
    sentences = payload.get("sentences")
    findings: list[dict[str, Any]] = []
    if not isinstance(sentences, list) or not sentences:
        findings.append(_finding("NO_SPOKEN_SENTENCES", "script.sentences must be a non-empty list"))
        sentences = []

    texts: list[tuple[str, str]] = []
    for index, item in enumerate(sentences):
        if not isinstance(item, dict) or not isinstance(item.get("text"), str) or not item["text"].strip():
            findings.append(_finding("INVALID_SENTENCE", "each sentence needs non-empty text", index=index))
            continue
        texts.append((str(item.get("sentence_id") or f"index-{index}"), item["text"].strip()))

    combined = "".join(text for _, text in texts)
    cjk_chars = len(re.findall(r"[\u3400-\u9fff]", combined))
    if min_cjk_chars is not None and cjk_chars < min_cjk_chars:
        findings.append(_finding("SCRIPT_TOO_SHORT", "spoken Chinese character count is below the locked range", actual=cjk_chars, minimum=min_cjk_chars))
    if max_cjk_chars is not None and cjk_chars > max_cjk_chars:
        findings.append(_finding("SCRIPT_TOO_LONG", "spoken Chinese character count exceeds the locked range", actual=cjk_chars, maximum=max_cjk_chars))

    marker_hits: list[dict[str, str]] = []
    for sentence_id, text in texts:
        for name, pattern in META_PATTERNS:
            if pattern.search(text):
                marker_hits.append({"sentence_id": sentence_id, "marker": name, "text": text})
    if len(marker_hits) > max_meta_markers:
        findings.append(
            _finding(
                "META_SCAFFOLDING_DENSITY",
                "narration exposes the writer's reasoning scaffold instead of settled audience-facing prose",
                actual=len(marker_hits),
                maximum=max_meta_markers,
                hits=marker_hits,
            )
        )

    question_ids = [sentence_id for sentence_id, text in texts if "？" in text or "?" in text]
    if len(question_ids) > max_rhetorical_questions:
        findings.append(
            _finding(
                "RHETORICAL_QUESTION_CHAIN",
                "too many narrated questions create self-dialogue rather than direct exposition",
                actual=len(question_ids),
                maximum=max_rhetorical_questions,
                sentence_ids=question_ids,
            )
        )

    return {
        "schema": "swainwong.script-style-gate.v1",
        "status": "PASS" if not findings else "REVISE",
        "metrics": {
            "sentence_count": len(texts),
            "cjk_character_count": cjk_chars,
            "meta_marker_count": len(marker_hits),
            "rhetorical_question_count": len(question_ids),
        },
        "policy": {
            "min_cjk_chars": min_cjk_chars,
            "max_cjk_chars": max_cjk_chars,
            "max_meta_markers": max_meta_markers,
            "max_rhetorical_questions": max_rhetorical_questions,
        },
        "findings": findings,
        "creative_review_required": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--script", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--min-cjk-chars", type=int)
    parser.add_argument("--max-cjk-chars", type=int)
    parser.add_argument("--max-meta-markers", type=int, default=2)
    parser.add_argument("--max-rhetorical-questions", type=int, default=3)
    args = parser.parse_args()
    payload = json.loads(args.script.read_text(encoding="utf-8"))
    report = evaluate_script(
        payload,
        min_cjk_chars=args.min_cjk_chars,
        max_cjk_chars=args.max_cjk_chars,
        max_meta_markers=args.max_meta_markers,
        max_rhetorical_questions=args.max_rhetorical_questions,
    )
    report["input"] = {
        "path": str(args.script.resolve()),
        "sha256": hashlib.sha256(args.script.read_bytes()).hexdigest(),
    }
    output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(output, encoding="utf-8")
    print(output, end="")
    raise SystemExit(0 if report["status"] == "PASS" else 2)


if __name__ == "__main__":
    main()
