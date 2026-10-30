from pathlib import Path
import sys
import json
import tempfile
import unittest


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = PLUGIN_ROOT / "skills" / "swainwong-video-workflow" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import serve_video_review  # noqa: E402


class VideoReviewAccessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp.cleanup()

    def state(self, status="NOT_STARTED", candidate_sha="a" * 64):
        readiness = Path(self.temp.name) / "owner-review-ready.json"
        readiness.write_text(json.dumps({
            "schema": "swainwong.owner-review-ready.v1",
            "candidate_sha256": candidate_sha,
            "candidate_internal_gate_sha256": "d" * 64,
        }), encoding="utf-8")
        return {
            "stages": {
                "owner-review-ready": {
                    "status": status,
                    "artifacts": [{
                        "path": str(readiness),
                        "sha256": "b" * 64,
                    }],
                }
            }
        }

    def test_internal_diagnostic_page_does_not_claim_owner_readiness(self):
        result = serve_video_review.review_audience_status(self.state(), "a" * 64, "internal")
        self.assertEqual(result["audience"], "internal")
        self.assertFalse(result["owner_review_ready"])
        self.assertIn("diagnostic", result["label"].lower())

    def test_owner_page_rejects_candidate_before_internal_gate(self):
        with self.assertRaisesRegex(ValueError, "owner-review-ready"):
            serve_video_review.review_audience_status(self.state(), "a" * 64, "owner")

    def test_owner_page_rejects_hash_mismatch(self):
        with self.assertRaisesRegex(ValueError, "candidate hash"):
            serve_video_review.review_audience_status(self.state("READY", "a" * 64), "c" * 64, "owner")

    def test_owner_page_accepts_exact_ready_candidate(self):
        result = serve_video_review.review_audience_status(self.state("READY", "a" * 64), "a" * 64, "owner")
        self.assertEqual(result["audience"], "owner")
        self.assertTrue(result["owner_review_ready"])


if __name__ == "__main__":
    unittest.main()
