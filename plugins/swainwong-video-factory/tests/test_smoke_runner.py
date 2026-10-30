import json
from pathlib import Path
import sys
import tempfile
import unittest


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))

import run_smoke_test  # noqa: E402


class SmokeRunnerTests(unittest.TestCase):
    def test_prepares_real_state_and_research_packet_without_fake_outputs(self):
        fixture = PLUGIN_ROOT / "tests" / "fixtures" / "smoke-brief.json"
        brief = json.loads(fixture.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "topic-smoke"
            report = run_smoke_test.run(project, brief)

            self.assertEqual(report["status"], "READY_FOR_RESEARCH")
            self.assertEqual(report["brief_id"], brief["brief_id"])
            self.assertEqual(report["topic"], brief["topic"])
            self.assertTrue(report["task_packet"]["dispatchable"])
            self.assertEqual(report["task_packet"]["role"], "01-research")
            self.assertEqual(report["task_packet"]["stage"], "research")
            self.assertEqual(report["completed_gates"], ["plugin_layout", "brief_lock", "research_dispatch"])
            self.assertIn("rendered_video", report["not_yet_exercised"])

            state = json.loads((project / ".video-workflow" / "state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["brief"]["brief_id"], brief["brief_id"])
            self.assertEqual(state["stages"]["research"]["status"], "NOT_STARTED")
            self.assertFalse(any(project.rglob("*.mp4")))
            self.assertTrue((project / ".video-workflow" / "research-task-packet.json").is_file())
            self.assertTrue((project / ".video-workflow" / "smoke-report.json").is_file())


if __name__ == "__main__":
    unittest.main()
