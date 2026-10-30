import importlib.util
from pathlib import Path
import unittest


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = PLUGIN_ROOT / "skills" / "swainwong-video-workflow" / "scripts"


def load_module(name: str):
    path = SCRIPTS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ScriptStyleGateTests(unittest.TestCase):
    def test_rejects_thought_process_scaffolding_density(self):
        gate = load_module("script_style_gate")
        payload = {
            "sentences": [
                {"sentence_id": "S001", "text": "先把这个数字说清楚。"},
                {"sentence_id": "S002", "text": "真正的问题是，大家为什么来？"},
                {"sentence_id": "S003", "text": "如果答案只是便宜，显然没这么简单。"},
                {"sentence_id": "S004", "text": "先排除一个最省事的答案。"},
                {"sentence_id": "S005", "text": "更准确的说法，是它降低了决策成本。"},
            ]
        }
        report = gate.evaluate_script(payload, max_meta_markers=2)
        self.assertEqual(report["status"], "REVISE")
        self.assertIn("META_SCAFFOLDING_DENSITY", {item["code"] for item in report["findings"]})

    def test_accepts_direct_final_prose(self):
        gate = load_module("script_style_gate")
        payload = {
            "sentences": [
                {"sentence_id": "S001", "text": "八天客流超过四百五十万人次。"},
                {"sentence_id": "S002", "text": "胖东来把商品信息、售后和现场服务做成了一套降低决策成本的系统。"},
                {"sentence_id": "S003", "text": "顾客因此更容易判断，也更敢于购买。"},
            ]
        }
        report = gate.evaluate_script(payload, max_meta_markers=2)
        self.assertEqual(report["status"], "PASS")


class SubtitlePhraseGateTests(unittest.TestCase):
    def test_rejects_sentence_sized_bilingual_blocks(self):
        gate = load_module("subtitle_phrase_gate")
        zh = """WEBVTT

S001
00:00:00.000 --> 00:00:07.870
先把四百五十万说清楚：二零二五年双节八天，许昌地区胖东来集团客流超过四百五十万人次。
"""
        en = """WEBVTT

S001
00:00:00.000 --> 00:00:07.870
First, let us clarify the 4.5 million figure: it was the total foot traffic across the group during the eight-day holiday.
"""
        report = gate.evaluate_vtt_pair(zh, en)
        self.assertEqual(report["status"], "REVISE")
        codes = {item["code"] for item in report["findings"]}
        self.assertTrue({"CUE_TOO_LONG", "ZH_TOO_MANY_CHARS"} & codes)

    def test_accepts_aligned_short_semantic_phrases(self):
        gate = load_module("subtitle_phrase_gate")
        zh = """WEBVTT

S001.1
00:00:00.040 --> 00:00:02.037
八天客流超过四百五十万人次

S001.2
00:00:02.037 --> 00:00:04.200
这不是四百五十万个不同的人
"""
        en = """WEBVTT

S001.1
00:00:00.040 --> 00:00:02.037
Foot traffic topped 4.5 million in eight days

S001.2
00:00:02.037 --> 00:00:04.200
That does not mean 4.5 million unique people
"""
        report = gate.evaluate_vtt_pair(zh, en)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["metrics"]["cue_count"], 2)

    def test_rejects_unpaired_timing(self):
        gate = load_module("subtitle_phrase_gate")
        zh = """WEBVTT

S001.1
00:00:00.000 --> 00:00:02.000
八天客流超过四百五十万人次
"""
        en = """WEBVTT

S001.1
00:00:00.100 --> 00:00:02.000
Foot traffic topped 4.5 million in eight days
"""
        report = gate.evaluate_vtt_pair(zh, en)
        self.assertEqual(report["status"], "REVISE")
        self.assertIn("PAIR_TIMING_MISMATCH", {item["code"] for item in report["findings"]})


if __name__ == "__main__":
    unittest.main()
