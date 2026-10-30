#!/usr/bin/env python3
"""Local, dependency-free MCP boundary for the video workflow state and feedback harness."""
from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any, Callable


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = PLUGIN_ROOT / "skills" / "swainwong-video-workflow" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import harness_feedback  # noqa: E402
import workflow_state  # noqa: E402


def _object_schema(properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }


PATH = {"type": "string", "description": "Absolute filesystem path."}


class WorkflowMCP:
    """Small synchronous MCP server whose writes delegate to canonical workflow functions."""

    def __init__(self) -> None:
        self._tools = {
            "workflow_initialize_project": (
                "Validate a human-confirmed brief and initialize persistent workflow state.",
                _object_schema({"project": PATH, "brief": {"type": "object"}}, ["project", "brief"]),
                self._initialize_project,
            ),
            "workflow_get_state": (
                "Read the persistent workflow state for a project.",
                _object_schema({"project": PATH}, ["project"]),
                self._get_state,
            ),
            "workflow_build_task_packet": (
                "Build a role-specific task packet from the current state and upstream evidence.",
                _object_schema({"project": PATH, "role": {"type": "string"}}, ["project", "role"]),
                self._build_task_packet,
            ),
            "workflow_record_stage": (
                "Record a stage result after deterministic dependency, artifact and hash checks.",
                _object_schema(
                    {
                        "project": PATH,
                        "stage": {"type": "string"},
                        "status": {"type": "string"},
                        "artifacts": {"type": "array", "items": PATH},
                        "evidence": {"type": "string"},
                        "target_sha256": {"type": "string"},
                    },
                    ["project", "stage", "status", "artifacts", "evidence"],
                ),
                self._record_stage,
            ),
            "feedback_capture_evidence": (
                "Recapture hash-bound media evidence for an immutable review submission.",
                _object_schema({"snapshot": PATH}, ["snapshot"]),
                self._capture_evidence,
            ),
            "feedback_record_analysis": (
                "Persist Agent analysis while keeping project repair and rule candidates distinct.",
                _object_schema({"snapshot": PATH, "analysis": {"type": "object"}}, ["snapshot", "analysis"]),
                self._record_analysis,
            ),
            "feedback_get_progress": (
                "Read feedback progress after validating snapshot, submission and video identity.",
                _object_schema({"snapshot": PATH}, ["snapshot"]),
                self._get_progress,
            ),
            "feedback_promote_candidate": (
                "Promote a candidate only with version-bound independent review and user confirmation.",
                _object_schema({"candidate": PATH, "approval": {"type": "object"}}, ["candidate", "approval"]),
                self._promote_candidate,
            ),
        }

    def _initialize_project(self, args: dict[str, Any]) -> dict[str, Any]:
        return workflow_state.initialize_project(Path(args["project"]), args["brief"])

    def _get_state(self, args: dict[str, Any]) -> dict[str, Any]:
        return workflow_state.get_state(Path(args["project"]))

    def _build_task_packet(self, args: dict[str, Any]) -> dict[str, Any]:
        return workflow_state.build_task_packet(Path(args["project"]), args["role"])

    def _record_stage(self, args: dict[str, Any]) -> dict[str, Any]:
        return workflow_state.record_stage(
            Path(args["project"]),
            args["stage"],
            args["status"],
            [Path(path) for path in args["artifacts"]],
            evidence=args["evidence"],
            target_sha256=args.get("target_sha256"),
        )

    def _capture_evidence(self, args: dict[str, Any]) -> dict[str, Any]:
        return harness_feedback.recapture(Path(args["snapshot"]))

    def _record_analysis(self, args: dict[str, Any]) -> dict[str, Any]:
        return harness_feedback.record_analysis(Path(args["snapshot"]), args["analysis"])

    def _get_progress(self, args: dict[str, Any]) -> dict[str, Any]:
        snapshot_path, snapshot = harness_feedback.load_snapshot(Path(args["snapshot"]))
        progress_path = snapshot_path.parent / "harness-progress.json"
        if not progress_path.is_file():
            return {
                "schema_version": 1,
                "submission_id": snapshot["id"],
                "video_sha256": snapshot["video"]["sha256"],
                "status": "awaiting_agent",
            }
        progress = json.loads(progress_path.read_text(encoding="utf-8"))
        if progress.get("submission_id") != snapshot["id"]:
            raise ValueError("反馈进度与提交号不一致")
        if progress.get("video_sha256") != snapshot["video"]["sha256"]:
            raise ValueError("反馈进度与视频哈希不一致")
        return progress

    def _promote_candidate(self, args: dict[str, Any]) -> dict[str, Any]:
        return harness_feedback.promote(Path(args["candidate"]), args["approval"])

    @staticmethod
    def _success(result: Any) -> dict[str, Any]:
        return {
            "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
            "structuredContent": result,
            "isError": False,
        }

    @staticmethod
    def _failure(exc: Exception) -> dict[str, Any]:
        message = f"{type(exc).__name__}: {exc}"
        return {"content": [{"type": "text", "text": message}], "isError": True}

    def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        method = request.get("method")
        if method == "initialize":
            requested = request.get("params", {}).get("protocolVersion", "2025-06-18")
            supported = {"2024-11-05", "2025-03-26", "2025-06-18", "2025-11-25"}
            return {
                "protocolVersion": requested if requested in supported else "2025-06-18",
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "swainwong-video-workflow", "version": "0.1.0"},
            }
        if method == "notifications/initialized":
            return {}
        if method == "ping":
            return {}
        if method == "tools/list":
            return {
                "tools": [
                    {"name": name, "description": spec[0], "inputSchema": spec[1]}
                    for name, spec in self._tools.items()
                ]
            }
        if method == "tools/call":
            params = request.get("params", {})
            name = params.get("name")
            if name not in self._tools:
                return self._failure(ValueError(f"未知工具：{name}"))
            try:
                return self._success(self._tools[name][2](params.get("arguments", {})))
            except (KeyError, OSError, TypeError, ValueError) as exc:
                return self._failure(exc)
        raise ValueError(f"Unsupported MCP method: {method}")


def _response(request: dict[str, Any], server: WorkflowMCP) -> dict[str, Any] | None:
    if "id" not in request:
        if request.get("method") == "notifications/initialized":
            server.handle(request)
        return None
    try:
        result = server.handle(request)
        return {"jsonrpc": "2.0", "id": request["id"], "result": result}
    except Exception as exc:  # JSON-RPC boundary; tool errors are handled above.
        return {
            "jsonrpc": "2.0",
            "id": request["id"],
            "error": {"code": -32603, "message": f"{type(exc).__name__}: {exc}"},
        }


def main() -> None:
    server = WorkflowMCP()
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            request = json.loads(line)
            response = _response(request, server)
        except Exception as exc:
            response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"{type(exc).__name__}: {exc}"},
            }
        if response is not None:
            print(json.dumps(response, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
