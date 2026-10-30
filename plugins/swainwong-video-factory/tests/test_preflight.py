import importlib.util
from pathlib import Path
import unittest


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PLUGIN_ROOT / "skills" / "swainwong-video-workflow" / "scripts" / "preflight.py"
SPEC = importlib.util.spec_from_file_location("video_workflow_preflight", SCRIPT)
preflight = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(preflight)


class PreflightTests(unittest.TestCase):
    def test_current_runtime_satisfies_hard_gate_dependencies(self):
        result = preflight.inspect_runtime()
        self.assertEqual(result["status"], "PASS", result)
        self.assertEqual(result["missing"], [])


if __name__ == "__main__":
    unittest.main()
