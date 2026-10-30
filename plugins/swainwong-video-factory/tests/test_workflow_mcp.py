import json
from pathlib import Path
import sys
import tempfile
import unittest
import uuid


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SERVER = PLUGIN_ROOT / "server"
sys.path.insert(0, str(SERVER))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import workflow_mcp  # noqa: E402
from test_workflow_state import valid_brief  # noqa: E402


class WorkflowMCPTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.project = Path(self.temp.name) / "project"
        self.server = workflow_mcp.WorkflowMCP()

    def tearDown(self):
        self.temp.cleanup()

    def request(self, method, params=None):
        return self.server.handle({"jsonrpc": "2.0", "id": "test", "method": method, "params": params or {}})

    def call(self, name, arguments):
        return self.request("tools/call", {"name": name, "arguments": arguments})

    def test_initialize_and_tool_discovery(self):
        initialized = self.request("initialize", {"protocolVersion": "2025-06-18"})
        self.assertEqual(initialized["serverInfo"]["name"], "swainwong-video-workflow")
        tools = self.request("tools/list")["tools"]
        self.assertEqual(
            {item["name"] for item in tools},
            {
                "workflow_initialize_project",
                "workflow_get_state",
                "workflow_build_task_packet",
                "workflow_record_stage",
                "feedback_capture_evidence",
                "feedback_record_analysis",
                "feedback_get_progress",
                "feedback_promote_candidate",
            },
        )

    def test_state_tools_persist_project_and_return_structured_content(self):
        created = self.call(
            "workflow_initialize_project",
            {"project": str(self.project), "brief": valid_brief()},
        )
        self.assertFalse(created["isError"])
        self.assertEqual(created["structuredContent"]["stages"]["brief"]["status"], "READY")
        state = self.call("workflow_get_state", {"project": str(self.project)})
        self.assertFalse(state["isError"])
        self.assertEqual(state["structuredContent"]["brief"]["brief_id"], "smoke-video")

    def test_invalid_write_returns_tool_error_without_corrupting_state(self):
        self.call("workflow_initialize_project", {"project": str(self.project), "brief": valid_brief()})
        artifact = self.project / "script.md"
        artifact.write_text("script", encoding="utf-8")
        result = self.call(
            "workflow_record_stage",
            {
                "project": str(self.project),
                "stage": "scriptwriting",
                "status": "READY",
                "artifacts": [str(artifact)],
                "evidence": "self-check",
            },
        )
        self.assertTrue(result["isError"])
        self.assertIn("research", result["content"][0]["text"])
        state = self.call("workflow_get_state", {"project": str(self.project)})["structuredContent"]
        self.assertEqual(state["stages"]["scriptwriting"]["status"], "NOT_STARTED")

    def test_feedback_progress_is_bound_to_snapshot_identity(self):
        video_sha = "a" * 64
        submission = str(uuid.uuid4())
        folder = self.project / "review-feedback" / video_sha / "submissions" / submission
        folder.mkdir(parents=True)
        snapshot_path = folder / "snapshot.json"
        snapshot = {
            "id": submission,
            "project": str(self.project.resolve()),
            "video": {"sha256": video_sha},
            "snapshot_file": str(snapshot_path.resolve()),
        }
        snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")
        progress = {
            "schema_version": 1,
            "submission_id": submission,
            "video_sha256": video_sha,
            "status": "analyzed",
        }
        (folder / "harness-progress.json").write_text(json.dumps(progress), encoding="utf-8")
        result = self.call("feedback_get_progress", {"snapshot": str(snapshot_path)})
        self.assertFalse(result["isError"])
        self.assertEqual(result["structuredContent"], progress)


if __name__ == "__main__":
    unittest.main()
