import hashlib
import json
from pathlib import Path
import copy
import subprocess
import sys
import tempfile
import unittest


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = PLUGIN_ROOT / "skills" / "swainwong-video-workflow" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import workflow_state  # noqa: E402
import final_visual_gate  # noqa: E402
import script_style_gate  # noqa: E402
import subtitle_phrase_gate  # noqa: E402


def valid_brief():
    return {
        "brief_id": "smoke-video",
        "revision": 1,
        "brief_confirmed": True,
        "confirmation_basis": "User explicitly confirmed this complete brief.",
        "topic": "Why ordinary objects become cultural symbols",
        "viewpoint": "Investigate the mechanism without pre-locking the conclusion.",
        "audience": "General Chinese-speaking viewers",
        "purpose": "Produce a concise evidence-led explainer",
        "aspect_ratio": "16:9",
        "duration": {
            "target_seconds": 180,
            "tolerance_before_seconds": 30,
            "tolerance_after_seconds": 30,
        },
        "voice": {
            "spoken_language": "zh-CN",
            "source": "human_recording",
            "profile_ref": "SwainWong",
            "verification_status": "verified",
        },
        "subtitles": {
            "language": "zh-CN",
            "render_authority": "openfilm-global-overlay-only",
        },
        "visual": {
            "asset_policy": "raster-and-footage-only",
            "forbidden_asset_types": ["svg", "code-vector", "generic-vector-illustration"],
            "third_party_primary_min_ratio": 0.7,
            "third_party_internal_video_min_ratio": 0.7,
        },
        "platform": "OpenFilm",
        "delivery": {"resolution": "1920x1080", "scope": "local_review"},
        "brand": {"logo_mode": "SwainTalk", "visual_style": "paper_explainer"},
        "a_roll": {"mode": "none"},
        "budget": "local-tools-only",
        "cleanup_policy": "preserve-sources-and-referenced-assets",
        "collaboration": "main-agent-coordinates-specialists",
    }


class WorkflowStateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.project = Path(self.temp.name) / "project"

    def tearDown(self):
        self.temp.cleanup()

    def artifact(self, name, content=None):
        path = self.project / "artifacts" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content or name, encoding="utf-8")
        return path

    def valid_storyboard(self, *, five_second_wall=False):
        capture = self.artifact("evidence/capture.png", "opened source capture")
        capture_sha = hashlib.sha256(capture.read_bytes()).hexdigest()
        if five_second_wall:
            intervals = [(0.0, 5.0), (5.0, 10.0), (10.0, 15.0), (15.0, 20.0)]
            body_end = 20.0
            total_end = 22.0
            segments = [("CH01", 0.0, 10.0), ("CH02", 10.0, 20.0), ("CREDITS", 20.0, 22.0)]
        else:
            intervals = [(0.0, 2.4), (2.4, 5.2), (5.2, 7.4), (7.4, 10.0)]
            body_end = 10.0
            total_end = 12.0
            segments = [("CH01", 0.0, 5.0), ("CH02", 5.0, 10.0), ("CREDITS", 10.0, 12.0)]

        units = [
            {
                "unit_id": "U1", "visual_unit_id": "U1", "primary_type": "third-party-footage", "coverage_class": "third_party_primary",
                "timeline": {"start_seconds": intervals[0][0], "end_seconds": intervals[0][1], "duration_seconds": intervals[0][1] - intervals[0][0]},
                "sentence_ids": ["S001"], "claim_ids": ["C001"], "fact_source_ids": ["SRC001"],
                "evidence_overlay_origin_ids": ["official-page::SRC001"], "event_date_scope": "2025 test scope", "semantic_status": "direct_evidence",
                "visible_evidence": [{
                    "claim_id": "C001", "fact_source_id": "SRC001", "evidence_origin_id": "official-page::SRC001",
                    "locator_or_crop": "paragraph 1", "date_scope": "2025 test scope",
                    "on_screen_start_seconds": intervals[0][0] + 0.1, "on_screen_end_seconds": intervals[0][1] - 0.1,
                    "capture_receipts": [{
                        "receipt_id": "SRC001-R1", "opened_at": "2026-10-29T00:00:00+08:00", "response_status": 200,
                        "final_url_or_file": "https://example.test/source", "exact_locator": "paragraph 1",
                        "capture_path": str(capture), "capture_sha256": capture_sha,
                    }],
                }],
            },
            {
                "unit_id": "U2", "visual_unit_id": "U2", "primary_type": "third-party-footage", "coverage_class": "third_party_primary",
                "timeline": {"start_seconds": intervals[1][0], "end_seconds": intervals[1][1], "duration_seconds": intervals[1][1] - intervals[1][0]},
                "sentence_ids": ["S002"], "claim_ids": [], "fact_source_ids": [], "evidence_overlay_origin_ids": [],
                "visible_evidence": [], "event_date_scope": "not applicable", "semantic_status": "contextual",
            },
            {
                "unit_id": "U3", "visual_unit_id": "U3", "primary_type": "third-party-image", "coverage_class": "third_party_primary",
                "timeline": {"start_seconds": intervals[2][0], "end_seconds": intervals[2][1], "duration_seconds": intervals[2][1] - intervals[2][0]},
                "sentence_ids": ["S003"], "claim_ids": [], "fact_source_ids": [], "evidence_overlay_origin_ids": [],
                "visible_evidence": [], "event_date_scope": "not applicable", "semantic_status": "illustrative_only",
            },
            {
                "unit_id": "U4", "visual_unit_id": "U4", "primary_type": "original-raster-animation", "coverage_class": "original_explanation",
                "timeline": {"start_seconds": intervals[3][0], "end_seconds": intervals[3][1], "duration_seconds": intervals[3][1] - intervals[3][0]},
                "sentence_ids": ["S004"], "claim_ids": [], "fact_source_ids": [], "evidence_overlay_origin_ids": [],
                "visible_evidence": [], "event_date_scope": "not applicable", "semantic_status": "original_explanation",
            },
        ]
        epsilon = 0.001
        boundaries = [segments[0][2], segments[1][2]]
        probes = []
        for index, boundary in enumerate(boundaries):
            for offset in (-epsilon, 0.0, epsilon):
                t = round(boundary + offset, 6)
                active = segments[index][0] if offset < 0 else segments[index + 1][0]
                probes.append({
                    "t": t,
                    "global_fill_px": round(1920 * t / total_end, 6),
                    "active_segment": active,
                    "reset_observed": False,
                })
        third_party_seconds = sum(end - start for start, end in intervals[:3])
        video_seconds = sum(end - start for start, end in intervals[:2])
        return {
            "schema": "swainwong.storyboard.audience-visual-units.v5",
            "workflow_contract_version": "4.9",
            "role_status": "READY",
            "audience_visual_units": units,
            "credit_units": [{"credit_unit_id": "C1", "start_seconds": body_end, "end_seconds": total_end, "semantic_status": "credits"}],
            "ratio_contract": {
                "third_party_seconds": third_party_seconds,
                "third_party_ratio": third_party_seconds / body_end,
                "third_party_video_seconds": video_seconds,
                "video_ratio_within_third_party": video_seconds / third_party_seconds,
            },
            "persistent_layers": {"progress": {
                "canvas": {"width": 1920, "height": 1080, "total_duration_seconds": total_end},
                "global_fill": {"reset_per_shot": False, "width_formula": f"1920*clamp(t/{total_end:g},0,1)"},
                "segments": [
                    {"chapter_id": chapter, "start_seconds": start, "end_seconds": end, "label": chapter}
                    for chapter, start, end in segments
                ],
                "actual_chapter_boundaries_seconds": boundaries,
                "boundary_epsilon_seconds": epsilon,
                "required_boundary_tests_seconds": [item["t"] for item in probes],
                "boundary_expectations": probes,
            }},
        }

    def prepare_storyboard_dependencies(self):
        workflow_state.initialize_project(self.project, valid_brief())
        self.ready("research")
        script = self.ready("scriptwriting")
        script_sha = script["stages"]["scriptwriting"]["artifacts"][0]["sha256"]
        self.ready("g1-director-review", script_sha)
        self.ready("g1-fact-review", script_sha)

    def record_storyboard(self, storyboard, status="READY"):
        path = self.artifact("storyboard.json", json.dumps(storyboard))
        return workflow_state.record_stage(
            self.project, "storyboard", status, [path], evidence="storyboard machine contract",
        )

    def ready(self, stage, target_sha256=None):
        if stage == "scriptwriting":
            content = {"sentences": [
                {"sentence_id": "S001", "text": "八天客流超过四百五十万人次。"},
                {"sentence_id": "S002", "text": "这套系统降低了顾客的决策成本。"},
            ]}
            path = self.artifact("scriptwriting.json", json.dumps(content))
            report_path = self.script_style_report(path)
            artifacts = [path, report_path]
        else:
            content = self.valid_storyboard() if stage == "storyboard" else {"stage": stage}
            path = self.artifact(f"{stage}.json", json.dumps(content))
            artifacts = [path]
        return workflow_state.record_stage(
            self.project,
            stage,
            "READY",
            artifacts,
            evidence=f"verified {stage}",
            target_sha256=target_sha256,
        )

    def script_style_report(self, script_path, name="script-style-gate.json"):
        content = json.loads(script_path.read_text(encoding="utf-8"))
        report = script_style_gate.evaluate_script(content)
        report["input"] = {"path": str(script_path.resolve()), "sha256": hashlib.sha256(script_path.read_bytes()).hexdigest()}
        return self.artifact(name, json.dumps(report))

    def subtitle_phrase_artifacts(self):
        zh = self.artifact("subtitles.zh.vtt", """WEBVTT

S001.1
00:00:00.000 --> 00:00:02.000
八天客流超过四百五十万人次
""")
        en = self.artifact("subtitles.en.vtt", """WEBVTT

S001.1
00:00:00.000 --> 00:00:02.000
Foot traffic topped 4.5 million in eight days
""")
        report = subtitle_phrase_gate.evaluate_vtt_pair(zh.read_text(), en.read_text())
        report["inputs"] = {
            "zh_vtt": {"path": str(zh.resolve()), "sha256": hashlib.sha256(zh.read_bytes()).hexdigest()},
            "en_vtt": {"path": str(en.resolve()), "sha256": hashlib.sha256(en.read_bytes()).hexdigest()},
        }
        report_path = self.artifact("subtitle-phrase-gate.json", json.dumps(report))
        return zh, en, report_path

    def test_storyboard_ready_accepts_recomputed_canonical_contract(self):
        self.prepare_storyboard_dependencies()
        state = self.record_storyboard(self.valid_storyboard())
        self.assertEqual(state["stages"]["storyboard"]["status"], "READY")

    def test_storyboard_ready_rejects_missing_capture_receipt(self):
        self.prepare_storyboard_dependencies()
        storyboard = self.valid_storyboard()
        storyboard["audience_visual_units"][0]["visible_evidence"][0]["capture_receipts"] = []
        with self.assertRaisesRegex(ValueError, "capture receipt"):
            self.record_storyboard(storyboard)

    def test_storyboard_ready_rejects_http_error_capture_receipt(self):
        self.prepare_storyboard_dependencies()
        storyboard = self.valid_storyboard()
        storyboard["audience_visual_units"][0]["visible_evidence"][0]["capture_receipts"][0]["response_status"] = 404
        with self.assertRaisesRegex(ValueError, "capture receipt"):
            self.record_storyboard(storyboard)

    def test_storyboard_ready_rejects_capture_hash_mismatch(self):
        self.prepare_storyboard_dependencies()
        storyboard = self.valid_storyboard()
        storyboard["audience_visual_units"][0]["visible_evidence"][0]["capture_receipts"][0]["capture_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "capture receipt"):
            self.record_storyboard(storyboard)

    def test_storyboard_ready_rejects_missing_real_chapter_boundary_probe(self):
        self.prepare_storyboard_dependencies()
        storyboard = self.valid_storyboard()
        storyboard["persistent_layers"]["progress"]["boundary_expectations"] = [
            item for item in storyboard["persistent_layers"]["progress"]["boundary_expectations"]
            if item["t"] != 5.001
        ]
        with self.assertRaisesRegex(ValueError, "chapter progress"):
            self.record_storyboard(storyboard)

    def test_storyboard_ready_rejects_locked_coverage_shortfall(self):
        self.prepare_storyboard_dependencies()
        storyboard = self.valid_storyboard()
        for index in (1, 2):
            storyboard["audience_visual_units"][index]["primary_type"] = "original-raster-animation"
            storyboard["audience_visual_units"][index]["coverage_class"] = "original_explanation"
        with self.assertRaisesRegex(ValueError, "third-party coverage"):
            self.record_storyboard(storyboard)

    def test_storyboard_ready_rejects_locked_internal_video_shortfall(self):
        self.prepare_storyboard_dependencies()
        storyboard = self.valid_storyboard()
        storyboard["audience_visual_units"][1]["primary_type"] = "third-party-image"
        with self.assertRaisesRegex(ValueError, "third-party video coverage"):
            self.record_storyboard(storyboard)

    def test_storyboard_ready_ignores_forged_project_validator_pass(self):
        self.prepare_storyboard_dependencies()
        storyboard = self.valid_storyboard()
        for index in (1, 2):
            storyboard["audience_visual_units"][index]["primary_type"] = "original-raster-animation"
            storyboard["audience_visual_units"][index]["coverage_class"] = "original_explanation"
        canonical = self.artifact("storyboard.json", json.dumps(storyboard))
        forged = self.artifact("project-validator.json", json.dumps({
            "schema": "project.custom-storyboard-validator.v99",
            "status": "PASS",
            "failed_checks": [],
        }))
        with self.assertRaisesRegex(ValueError, "third-party coverage"):
            workflow_state.record_stage(
                self.project,
                "storyboard",
                "READY",
                [canonical, forged],
                evidence="project validator cannot override plugin recomputation",
            )

    def test_storyboard_ready_rejects_forbidden_vector_primary(self):
        self.prepare_storyboard_dependencies()
        storyboard = self.valid_storyboard()
        storyboard["audience_visual_units"][3]["primary_type"] = "code-vector"
        with self.assertRaisesRegex(ValueError, "forbidden primary"):
            self.record_storyboard(storyboard)

    def test_storyboard_ready_rejects_non_contiguous_evidence_origin_reuse(self):
        self.prepare_storyboard_dependencies()
        storyboard = self.valid_storyboard()
        storyboard["audience_visual_units"][2]["evidence_overlay_origin_ids"] = ["official-page::SRC001"]
        with self.assertRaisesRegex(ValueError, "evidence origin"):
            self.record_storyboard(storyboard)

    def test_storyboard_ready_rejects_fixed_five_second_wall(self):
        self.prepare_storyboard_dependencies()
        with self.assertRaisesRegex(ValueError, "five-second wall"):
            self.record_storyboard(self.valid_storyboard(five_second_wall=True))

    def test_storyboard_ready_rejects_wrong_contract_or_role_status(self):
        self.prepare_storyboard_dependencies()
        storyboard = self.valid_storyboard()
        storyboard["workflow_contract_version"] = "4.8"
        with self.assertRaisesRegex(ValueError, "workflow contract"):
            self.record_storyboard(storyboard)
        storyboard = self.valid_storyboard()
        storyboard["role_status"] = "PARTIAL"
        with self.assertRaisesRegex(ValueError, "role_status"):
            self.record_storyboard(storyboard)

    def test_storyboard_ready_rejects_timeline_gap(self):
        self.prepare_storyboard_dependencies()
        storyboard = self.valid_storyboard()
        storyboard["audience_visual_units"][1]["timeline"]["start_seconds"] = 2.5
        with self.assertRaisesRegex(ValueError, "timeline"):
            self.record_storyboard(storyboard)

    def test_storyboard_ready_rejects_missing_required_unit_fields(self):
        self.prepare_storyboard_dependencies()
        fields = ("unit_id", "primary_type", "sentence_ids", "event_date_scope", "semantic_status")
        for field in fields:
            with self.subTest(field=field):
                storyboard = self.valid_storyboard()
                storyboard["audience_visual_units"][1].pop(field)
                with self.assertRaisesRegex(ValueError, "unit contract"):
                    self.record_storyboard(storyboard)

    def test_storyboard_ready_rejects_visible_evidence_on_non_direct_unit(self):
        self.prepare_storyboard_dependencies()
        storyboard = self.valid_storyboard()
        storyboard["audience_visual_units"][1]["visible_evidence"] = copy.deepcopy(
            storyboard["audience_visual_units"][0]["visible_evidence"]
        )
        with self.assertRaisesRegex(ValueError, "visible evidence"):
            self.record_storyboard(storyboard)

    def test_non_ready_storyboard_status_preserves_invalid_evidence_without_gate(self):
        self.prepare_storyboard_dependencies()
        state = self.record_storyboard({"reason": "capture unavailable"}, status="REVISE")
        self.assertEqual(state["stages"]["storyboard"]["status"], "REVISE")

    def test_get_state_recomputes_storyboard_gate_against_capture_bytes(self):
        self.prepare_storyboard_dependencies()
        storyboard = self.valid_storyboard()
        self.record_storyboard(storyboard)
        Path(storyboard["audience_visual_units"][0]["visible_evidence"][0]["capture_receipts"][0]["capture_path"]).write_text(
            "capture bytes changed after READY",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValueError, "capture receipt"):
            workflow_state.get_state(self.project)

    def first_full_cut(self, script_sha, name="rough-cut.mp4"):
        rough_cut = self.project / "artifacts" / name
        rough_cut.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([
            "ffmpeg", "-y", "-v", "error",
            "-f", "lavfi", "-i", "color=c=black:s=16x16:r=1:d=180",
            "-f", "lavfi", "-i", "anullsrc=r=8000:cl=mono",
            "-t", "180", "-shortest", "-c:v", "libx264", "-preset", "ultrafast",
            "-c:a", "aac", "-pix_fmt", "yuv420p", str(rough_cut),
        ], check=True)
        rough_cut_sha = hashlib.sha256(rough_cut.read_bytes()).hexdigest()
        report = self.artifact(f"{Path(name).stem}-report.json", json.dumps({
            "schema": "swainwong.first-full-cut.v1",
            "stage": "editing-first-full-cut",
            "candidate": {"sha256": rough_cut_sha, "duration_seconds": 180},
            "script_sha256": script_sha,
            "coverage": {"start_seconds": 0, "end_seconds": 180, "missing_ranges": []},
            "technical": {
                "render_complete": True,
                "decode_status": "PASS",
                "audio_clock_present": True,
                "visual_track_present": True,
            },
            "placeholders": [{"segment_id": "S003", "kind": "temporary-footage"}],
        }))
        state = workflow_state.record_stage(
            self.project,
            "editing-first-full-cut",
            "READY",
            [rough_cut, report],
            evidence="complete rough cut rendered as soon as the production-ready script and coarse storyboard were ready",
        )
        return state, rough_cut_sha

    def video_artifact(self, name, color="black", duration=1.0, *, navigation=False, source_visuals=True):
        path = self.project / "artifacts" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        command = [
            "ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
            f"color=c={color}:s=320x180:r=10:d={duration}",
        ]
        if navigation:
            filters = []
            if source_visuals:
                filters.extend([
                    "drawbox=x=0:y=0:w=iw:h=ih:color=red:t=fill:enable='lt(t,0.4)'",
                    "drawbox=x=0:y=0:w=iw:h=ih:color=blue:t=fill:enable='between(t,0.4,0.8)'",
                    "drawbox=x=0:y=0:w=iw:h=ih:color=green:t=fill:enable='gte(t,0.8)'",
                ])
            filters.extend([
                "drawbox=x=20:y=5:w=24:h=3:color=white:t=fill",
                "drawbox=x=180:y=5:w=24:h=3:color=white:t=fill",
                "drawbox=x=128:y=3:w=1:h=9:color=white:t=fill",
                "drawbox=x=0:y=0:w=64:h=2:color=0xff2b8a:t=fill:enable='gte(t,0.15)'",
                "drawbox=x=0:y=0:w=96:h=2:color=0xff2b8a:t=fill:enable='gte(t,0.25)'",
                "drawbox=x=0:y=0:w=128:h=2:color=0xff2b8a:t=fill:enable='gte(t,0.35)'",
                "drawbox=x=0:y=0:w=160:h=2:color=0xff2b8a:t=fill:enable='gte(t,0.45)'",
                "drawbox=x=0:y=0:w=224:h=2:color=0xff2b8a:t=fill:enable='gte(t,0.65)'",
                "drawbox=x=0:y=0:w=320:h=2:color=0xff2b8a:t=fill:enable='gte(t,0.85)'",
                "drawbox=x=60:y=130:w=200:h=6:color=white:t=fill",
                "drawbox=x=80:y=150:w=160:h=5:color=white:t=fill",
            ])
            command.extend(["-vf", ",".join(filters)])
        command.extend(["-c:v", "libx264", "-pix_fmt", "yuv420p", str(path)])
        subprocess.run(command, check=True)
        return path

    def final_visual_gate(self, candidate, source_a, source_b, duration=1.0):
        candidate_sha = hashlib.sha256(candidate.read_bytes()).hexdigest()
        source_a_sha = hashlib.sha256(source_a.read_bytes()).hexdigest()
        source_b_sha = hashlib.sha256(source_b.read_bytes()).hexdigest()
        clean_references = []
        for index, color in enumerate(("red", "blue", "green"), start=1):
            clean_path = self.project / "artifacts" / f"clean-{index:02d}.png"
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"color=c={color}:s=320x180:d=0.1", "-frames:v", "1", str(clean_path)], check=True)
            clean_references.append((clean_path, hashlib.sha256(clean_path.read_bytes()).hexdigest()))
        manifest = {
            "schema": "swainwong.final-visual-gate-input.v2",
            "candidate": {"path": str(candidate), "sha256": candidate_sha, "duration_seconds": duration, "width": 320, "height": 180},
            "chapter_navigation": {
                "track": "single-full-width-segmented-navigation",
                "rendered_segment_count": 2,
                "rendered_separator_count": 1,
                "rendered_labels": ["问题", "机制"],
                "pixel_tolerance": 2.0,
                "chapters": [
                    {"label": "问题", "start_seconds": 0.0, "end_seconds": 0.4, "rendered_start_x": 0.0, "rendered_end_x": 128.0},
                    {"label": "机制", "start_seconds": 0.4, "end_seconds": 1.0, "rendered_start_x": 128.0, "rendered_end_x": 320.0},
                ],
                "pixel_samples": [
                    {"time_seconds": 0.0, "fill_x": 0.0},
                    {"time_seconds": 0.2, "fill_x": 64.0},
                    {"time_seconds": 0.3, "fill_x": 96.0},
                    {"time_seconds": 0.4, "fill_x": 128.0},
                    {"time_seconds": 0.5, "fill_x": 160.0},
                    {"time_seconds": 0.7, "fill_x": 224.0},
                    {"time_seconds": 1.0, "fill_x": 320.0},
                ],
            },
            "third_party_video_uses": [
                {"clip_id": "A1", "origin_id": "origin-a", "timeline_start": 0.0, "timeline_end": 0.4, "source_in": 0.0, "source_out": 0.4, "source_path": str(source_a), "source_sha256": source_a_sha, "source_width": 320, "source_height": 180, "render_width": 320, "render_height": 180, "zoom": 1.0, "composition_mode": "cover_full_frame"},
                {"clip_id": "B1", "origin_id": "origin-b", "timeline_start": 0.4, "timeline_end": 0.8, "source_in": 0.0, "source_out": 0.4, "source_path": str(source_b), "source_sha256": source_b_sha, "source_width": 320, "source_height": 180, "render_width": 320, "render_height": 180, "zoom": 1.0, "composition_mode": "cover_full_frame"},
            ],
            "third_party_image_uses": [],
            "coverage_policy": {"third_party_primary_min_ratio": 0.7, "third_party_internal_video_min_ratio": 0.7},
            "subtitle_policy": {"authority": "openfilm-final-burn-in", "expected_languages": ["zh", "en"], "minimum_pixel_proofs": 3},
            "subtitle_pixel_proofs": [
                {"cue_id": "S001", "time_seconds": 0.1, "clean_reference_path": str(clean_references[0][0]), "clean_reference_sha256": clean_references[0][1], "region": {"x": 20, "y": 110, "width": 280, "height": 60}},
                {"cue_id": "S002", "time_seconds": 0.5, "clean_reference_path": str(clean_references[1][0]), "clean_reference_sha256": clean_references[1][1], "region": {"x": 20, "y": 110, "width": 280, "height": 60}},
                {"cue_id": "S003", "time_seconds": 0.9, "clean_reference_path": str(clean_references[2][0]), "clean_reference_sha256": clean_references[2][1], "region": {"x": 20, "y": 110, "width": 280, "height": 60}},
            ],
            "audience_visual_units": [
                {"unit_id": "A1", "start_seconds": 0.0, "end_seconds": 0.4, "primary_type": "third-party-footage", "contains_readable_text": False, "sentence_ids": ["S001"], "claim_ids": ["C001"], "fact_source_ids": ["SRC001"], "evidence_overlay_origin_ids": ["official-page::SRC001"], "visible_evidence": [{"claim_id": "C001", "fact_source_id": "SRC001", "locator_or_crop": "paragraph 1", "date_scope": "test", "on_screen_start_seconds": 0.05, "on_screen_end_seconds": 0.35}], "event_date_scope": "test", "semantic_status": "direct_evidence"},
                {"unit_id": "B1", "start_seconds": 0.4, "end_seconds": 0.8, "primary_type": "third-party-footage", "contains_readable_text": False, "sentence_ids": ["S002"], "claim_ids": [], "fact_source_ids": [], "event_date_scope": "test", "semantic_status": "contextual"},
                {"unit_id": "N1", "start_seconds": 0.8, "end_seconds": 1.0, "primary_type": "original-raster-animation", "contains_readable_text": False, "sentence_ids": ["S003"], "claim_ids": [], "fact_source_ids": [], "event_date_scope": "not applicable", "semantic_status": "original_explanation"},
            ],
            "brand_overlay": {"anchor": "lower-right", "transparent": True, "backing_plate": False},
        }
        manifest_path = self.artifact("final-visual-gate-input.json", json.dumps(manifest))
        manifest_sha = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        report = final_visual_gate.validate_manifest(manifest, input_manifest_sha256=manifest_sha)
        report_path = self.artifact("final-visual-gate.json", json.dumps(report))
        return manifest_path, report_path

    def g3_review(self, stage, candidate_sha, duration=180):
        role = {
            "g3-director-review": "09-director-review",
            "g3-visual-review": "10-visual-review",
            "g3-fact-review": "11-fact-review",
        }[stage]
        reviewer = role + "-independent"
        capabilities = {
            "continuous_visual": stage != "g3-fact-review",
            "real_listening": stage == "g3-director-review",
            "fact_and_source_review": stage == "g3-fact-review",
        }
        report = self.artifact(f"{stage}.review.json", json.dumps({
            "schema": "swainwong.review.v1",
            "stage": stage,
            "role": role,
            "candidate_sha256": candidate_sha,
            "reviewer_id": reviewer,
            "producer_id": "07-editing-producer",
            "method": "continuous-normal-speed-final-file-review",
            "coverage": {"start_seconds": 0, "end_seconds": duration},
            "capabilities": capabilities,
            "status": "PASS",
            "findings": [],
            **({"visual_checks": {
                "visual_asset_policy": "PASS",
                "subtitle_single_authority": "PASS",
                "chapter_labels_and_segmentation_visual": "PASS",
                "brand_overlay_visual": "PASS",
                "source_perceived_quality": "PASS",
                "short_shot_readability": "PASS",
            }} if stage == "g3-visual-review" else {}),
            **({"fact_checks": {
                "source_semantic_fit": "PASS",
                "event_date_scope": "PASS",
                "claim_visual_alignment": "PASS",
            }} if stage == "g3-fact-review" else {}),
        }))
        state = workflow_state.record_stage(
            self.project,
            stage,
            "READY",
            [report],
            evidence=f"independent {role} review of the final candidate",
            target_sha256=candidate_sha,
        )
        return state, report

    def test_initialize_rejects_unconfirmed_or_incomplete_brief(self):
        brief = valid_brief()
        brief["brief_confirmed"] = False
        with self.assertRaisesRegex(ValueError, "brief_confirmed"):
            workflow_state.initialize_project(self.project, brief)
        brief = valid_brief()
        del brief["voice"]["profile_ref"]
        with self.assertRaisesRegex(ValueError, "voice.profile_ref"):
            workflow_state.initialize_project(self.project, brief)

    def test_initialize_requires_visual_asset_policy_and_subtitle_authority(self):
        brief = valid_brief()
        del brief["visual"]["asset_policy"]
        with self.assertRaisesRegex(ValueError, "visual.asset_policy"):
            workflow_state.initialize_project(self.project, brief)
        brief = valid_brief()
        del brief["subtitles"]["render_authority"]
        with self.assertRaisesRegex(ValueError, "subtitles.render_authority"):
            workflow_state.initialize_project(self.project, brief)

    def test_initialize_locks_canonical_brief_and_appends_event(self):
        state = workflow_state.initialize_project(self.project, valid_brief())
        brief_file = self.project / ".video-workflow" / "brief.json"
        expected = hashlib.sha256(brief_file.read_bytes()).hexdigest()
        self.assertEqual(state["brief"]["config_sha256"], expected)
        self.assertEqual(state["stages"]["brief"]["status"], "READY")
        self.assertEqual(state["stages"]["research"]["status"], "NOT_STARTED")
        events = (self.project / ".video-workflow" / "events.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(events), 1)
        self.assertEqual(json.loads(events[0])["event"], "project_initialized")

    def test_ready_stage_requires_ready_dependencies_and_real_artifacts(self):
        workflow_state.initialize_project(self.project, valid_brief())
        script = self.artifact("script.md")
        with self.assertRaisesRegex(ValueError, "research"):
            workflow_state.record_stage(
                self.project,
                "scriptwriting",
                "READY",
                [script],
                evidence="script check",
            )
        missing = self.project / "artifacts" / "missing.md"
        with self.assertRaisesRegex(ValueError, "missing"):
            workflow_state.record_stage(
                self.project,
                "research",
                "READY",
                [missing],
                evidence="research check",
            )

    def test_ready_stage_hashes_artifacts_and_unlocks_task_packet(self):
        workflow_state.initialize_project(self.project, valid_brief())
        research = self.artifact("research.json", "evidence")
        state = workflow_state.record_stage(
            self.project,
            "research",
            "READY",
            [research],
            evidence="claims and sources inspected",
        )
        self.assertEqual(
            state["stages"]["research"]["artifacts"][0]["sha256"],
            hashlib.sha256(research.read_bytes()).hexdigest(),
        )
        packet = workflow_state.build_task_packet(self.project, "02-scriptwriting")
        self.assertTrue(packet["dispatchable"])
        self.assertEqual(packet["stage"], "scriptwriting")
        self.assertEqual(packet["brief"]["config_sha256"], state["brief"]["config_sha256"])
        self.assertTrue(Path(packet["role_method"]).is_file())
        self.assertTrue(Path(packet["role_harness"]).is_file())
        self.assertEqual(packet["dependencies"]["research"]["status"], "READY")

    def test_get_state_rejects_unknown_status_and_artifact_hash_drift(self):
        workflow_state.initialize_project(self.project, valid_brief())
        research = self.artifact("research.json", "evidence")
        workflow_state.record_stage(
            self.project,
            "research",
            "READY",
            [research],
            evidence="claims and sources inspected",
        )
        research.write_text("changed after READY", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "artifact identity mismatch"):
            workflow_state.get_state(self.project)

        state_file = self.project / ".video-workflow" / "state.json"
        state = json.loads(state_file.read_text(encoding="utf-8"))
        research.write_text("evidence", encoding="utf-8")
        state["stages"]["research"]["status"] = "AVAILABLE_DIAGNOSTIC_ONLY"
        state_file.write_text(json.dumps(state), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "unsupported stored stage status"):
            workflow_state.get_state(self.project)

    def test_same_stage_can_explicitly_replace_a_mutated_artifact_but_other_stages_cannot(self):
        workflow_state.initialize_project(self.project, valid_brief())
        research = self.artifact("research.json", "evidence-v1")
        workflow_state.record_stage(self.project, "research", "READY", [research], evidence="research v1")
        script = self.artifact("script.json", json.dumps({"sentences": [{"sentence_id": "S001", "text": "这是已经完成的直接表达。"}]}))
        script_gate = self.script_style_report(script)
        workflow_state.record_stage(self.project, "scriptwriting", "READY", [script, script_gate], evidence="script v1")
        research.write_text("evidence-v2", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "artifact identity mismatch"):
            workflow_state.record_stage(self.project, "scriptwriting", "REVISE", [], evidence="must not bypass another stage drift")
        state = workflow_state.record_stage(self.project, "research", "READY", [research], evidence="explicit same-stage v2 replacement")
        self.assertEqual(state["stages"]["research"]["status"], "READY")
        self.assertEqual(state["stages"]["scriptwriting"]["status"], "STALE")
        self.assertEqual(state["stages"]["research"]["artifacts"][0]["sha256"], hashlib.sha256(research.read_bytes()).hexdigest())
        self.assertEqual(workflow_state.get_state(self.project)["stages"]["research"]["status"], "READY")

    def test_scriptwriting_ready_requires_recomputed_style_gate(self):
        workflow_state.initialize_project(self.project, valid_brief())
        self.ready("research")
        script = self.artifact("script.json", json.dumps({
            "sentences": [
                {"sentence_id": "S001", "text": "八天客流超过四百五十万人次。"},
                {"sentence_id": "S002", "text": "这套系统降低了顾客的决策成本。"},
            ]
        }))
        with self.assertRaisesRegex(ValueError, "script style gate"):
            workflow_state.record_stage(
                self.project,
                "scriptwriting",
                "READY",
                [script],
                evidence="script without its deterministic editorial report",
            )
    def test_ancestor_replacement_allows_descendant_drift_then_marks_every_descendant_stale(self):
        workflow_state.initialize_project(self.project, valid_brief())
        research = self.artifact("research.json", "evidence-v1")
        workflow_state.record_stage(self.project, "research", "READY", [research], evidence="research v1")
        script = self.artifact("script.json", json.dumps({"sentences": [{"sentence_id": "S001", "text": "这是已经完成的直接表达。"}]}))
        script_gate = self.script_style_report(script)
        workflow_state.record_stage(self.project, "scriptwriting", "READY", [script, script_gate], evidence="script v1")
        script_sha = hashlib.sha256(script.read_bytes()).hexdigest()
        self.ready("g1-director-review", script_sha)
        self.ready("g1-fact-review", script_sha)
        self.ready("storyboard")

        research.write_text("evidence-v2", encoding="utf-8")
        script.write_text(json.dumps({"sentences": [{"sentence_id": "S001", "text": "这是等待失效的新表达。"}]}), encoding="utf-8")
        state = workflow_state.record_stage(
            self.project,
            "research",
            "READY",
            [research],
            evidence="explicit ancestor replacement invalidates all downstream work",
        )

        self.assertEqual(state["stages"]["research"]["status"], "READY")
        descendants = workflow_state._descendants("research")
        self.assertIn("scriptwriting", descendants)
        self.assertTrue(descendants)
        previously_ready_descendants = {"scriptwriting", "g1-director-review", "g1-fact-review", "storyboard"}
        for stage in previously_ready_descendants:
            self.assertEqual(state["stages"][stage]["status"], "STALE", stage)
        self.assertTrue(previously_ready_descendants.issubset(descendants))
        self.assertEqual(workflow_state.get_state(self.project)["stages"]["scriptwriting"]["status"], "STALE")

    def test_stage_replacement_does_not_allow_unrelated_ready_stage_drift(self):
        workflow_state.initialize_project(self.project, valid_brief())
        self.ready("research")
        script = self.ready("scriptwriting")
        script_sha = script["stages"]["scriptwriting"]["artifacts"][0]["sha256"]
        director = self.ready("g1-director-review", script_sha)
        fact = self.ready("g1-fact-review", script_sha)
        director_path = Path(director["stages"]["g1-director-review"]["artifacts"][0]["path"])
        fact_path = Path(fact["stages"]["g1-fact-review"]["artifacts"][0]["path"])
        director_path.write_text("director review v2", encoding="utf-8")
        fact_path.write_text("unrelated fact review drift", encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "artifact identity mismatch for g1-fact-review"):
            workflow_state.record_stage(
                self.project,
                "g1-director-review",
                "READY",
                [director_path],
                evidence="replace director review only",
                target_sha256=script_sha,
            )

    def test_explicit_v1_migration_preserves_backup_and_normalizes_legacy_state(self):
        workflow_state.initialize_project(self.project, valid_brief())
        state_file = self.project / ".video-workflow" / "state.json"
        state = json.loads(state_file.read_text(encoding="utf-8"))
        state["schema_version"] = 1
        state["stages"].pop("candidate-internal-gate")
        state["stages"].pop("owner-review-ready")
        state["stages"]["feedback"]["status"] = "AVAILABLE_DIAGNOSTIC_ONLY"
        legacy_candidate = self.artifact("legacy-final.mp4", "not a playable current-schema candidate")
        state["stages"]["editing-final"] = {
            "status": "READY",
            "artifacts": [{
                "path": str(legacy_candidate),
                "sha256": hashlib.sha256(legacy_candidate.read_bytes()).hexdigest(),
                "size": legacy_candidate.stat().st_size,
            }],
            "evidence": "legacy self-reported READY",
            "updated_at": None,
        }
        state["current_stage"] = "legacy-parallel-truth"
        state_file.write_text(json.dumps(state), encoding="utf-8")

        migrated = workflow_state.migrate_state_v1(self.project)
        self.assertEqual(migrated["schema_version"], 2)
        self.assertEqual(migrated["stages"]["feedback"]["status"], "REVISE")
        self.assertEqual(migrated["stages"]["editing-final"]["status"], "REVISE")
        self.assertEqual(migrated["stages"]["candidate-internal-gate"]["status"], "NOT_STARTED")
        self.assertEqual(migrated["stages"]["owner-review-ready"]["status"], "NOT_STARTED")
        self.assertNotIn("current_stage", migrated)
        self.assertEqual(migrated["extensions"]["legacy_v1"]["current_stage"], "legacy-parallel-truth")
        backups = list((self.project / ".video-workflow").glob("state.v1.*.json"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(json.loads(backups[0].read_text(encoding="utf-8"))["schema_version"], 1)
        self.assertEqual(workflow_state.get_state(self.project)["schema_version"], 2)

    def test_changed_target_invalidates_bound_review_and_downstream(self):
        workflow_state.initialize_project(self.project, valid_brief())
        self.ready("research")
        script = self.ready("scriptwriting")
        script_sha = script["stages"]["scriptwriting"]["artifacts"][0]["sha256"]
        self.ready("g1-director-review", script_sha)
        self.ready("g1-fact-review", script_sha)
        storyboard = self.ready("storyboard")
        storyboard_sha = storyboard["stages"]["storyboard"]["artifacts"][0]["sha256"]
        self.ready("g1-visual-review", storyboard_sha)
        _, rough_cut_sha = self.first_full_cut(script_sha)
        self.ready("g2-director-review", rough_cut_sha)
        self.ready("g2-visual-review", rough_cut_sha)
        self.ready("g2-fact-review", rough_cut_sha)
        self.ready("voice")
        self.ready("assets")
        self.ready("bgm")
        animation = self.ready("animation")
        self.assertEqual(animation["stages"]["animation"]["status"], "READY")

        changed_storyboard = self.valid_storyboard()
        changed_storyboard["revision_note"] = "valid changed storyboard"
        changed = self.artifact("storyboard-v2.json", json.dumps(changed_storyboard))
        state = workflow_state.record_stage(
            self.project,
            "storyboard",
            "READY",
            [changed],
            evidence="storyboard revised and checked",
        )
        self.assertEqual(state["stages"]["g1-director-review"]["status"], "READY")
        self.assertEqual(state["stages"]["g1-visual-review"]["status"], "STALE")
        self.assertEqual(state["stages"]["g1-fact-review"]["status"], "READY")
        self.assertEqual(state["stages"]["editing-first-full-cut"]["status"], "STALE")
        self.assertEqual(state["stages"]["voice"]["status"], "STALE")
        self.assertEqual(state["stages"]["animation"]["status"], "STALE")
        events = [json.loads(line) for line in (self.project / ".video-workflow" / "events.jsonl").read_text().splitlines()]
        self.assertEqual(events[-1]["event"], "stage_recorded")
        self.assertIn("editing-first-full-cut", events[-1]["invalidated_stages"])

    def test_first_full_cut_requires_production_ready_script_but_not_final_assets(self):
        workflow_state.initialize_project(self.project, valid_brief())
        self.ready("research")

        rough_cut = self.artifact("rough-cut.mp4", "rough cut bytes")
        with self.assertRaisesRegex(ValueError, "scriptwriting"):
            workflow_state.record_stage(
                self.project,
                "editing-first-full-cut",
                "READY",
                [rough_cut],
                evidence="full-duration rough cut",
            )

        script_state = self.ready("scriptwriting")
        script_sha = script_state["stages"]["scriptwriting"]["artifacts"][0]["sha256"]
        self.ready("g1-director-review", script_sha)
        self.ready("g1-fact-review", script_sha)
        self.ready("storyboard")

        state, _ = self.first_full_cut(script_sha)
        self.assertEqual(state["stages"]["editing-first-full-cut"]["status"], "READY")
        self.assertEqual(state["stages"]["voice"]["status"], "NOT_STARTED")
        self.assertEqual(state["stages"]["assets"]["status"], "NOT_STARTED")
        self.assertEqual(state["stages"]["animation"]["status"], "NOT_STARTED")

    def test_owner_review_requires_final_visual_gate_g3_and_hash_bound_av_gate(self):
        workflow_state.initialize_project(self.project, valid_brief())
        self.ready("research")
        script = self.ready("scriptwriting")
        script_sha = script["stages"]["scriptwriting"]["artifacts"][0]["sha256"]
        self.ready("g1-director-review", script_sha)
        self.ready("g1-fact-review", script_sha)
        storyboard = self.ready("storyboard")
        storyboard_sha = storyboard["stages"]["storyboard"]["artifacts"][0]["sha256"]
        self.ready("g1-visual-review", storyboard_sha)
        _, rough_cut_sha = self.first_full_cut(script_sha)
        self.ready("g2-director-review", rough_cut_sha)
        self.ready("g2-visual-review", rough_cut_sha)
        self.ready("g2-fact-review", rough_cut_sha)
        self.ready("voice")
        self.ready("assets")
        self.ready("bgm")
        self.ready("animation")
        candidate = self.video_artifact("final.mp4", "black", 1.0, navigation=True)
        with self.assertRaisesRegex(ValueError, "final visual gate"):
            workflow_state.record_stage(
                self.project,
                "editing-final",
                "READY",
                [candidate],
                evidence="rendered candidate only",
            )

        candidate_sha = hashlib.sha256(candidate.read_bytes()).hexdigest()
        source_a = self.video_artifact("source-a.mp4", "red", 1.0)
        source_b = self.video_artifact("source-b.mp4", "blue", 1.0)
        forged = self.video_artifact("forged-black-with-navigation.mp4", "black", 1.0, navigation=True, source_visuals=False)
        forged_input, forged_gate = self.final_visual_gate(forged, source_a, source_b, 1.0)
        forged_report = json.loads(forged_gate.read_text(encoding="utf-8"))
        self.assertIn("third_party_source_appearance", forged_report["failed_checks"])
        with self.assertRaisesRegex(ValueError, "final visual gate must be PASS"):
            workflow_state.record_stage(
                self.project,
                "editing-final",
                "READY",
                [forged, forged_input, forged_gate],
                evidence="forged manifest claims sources that never appear in final pixels",
            )

        visual_input, visual_gate = self.final_visual_gate(candidate, source_a, source_b, 1.0)
        zh_vtt, en_vtt, subtitle_gate = self.subtitle_phrase_artifacts()
        state = workflow_state.record_stage(
            self.project,
            "editing-final",
            "READY",
            [candidate, visual_input, visual_gate, zh_vtt, en_vtt, subtitle_gate],
            evidence="candidate rendered and deterministic final visual contract passed",
        )
        self.assertEqual(state["stages"]["editing-final"]["status"], "READY")

        review_files = {}
        for stage in ("g3-director-review", "g3-visual-review", "g3-fact-review"):
            _, report = self.g3_review(stage, candidate_sha, 1.0)
            review_files[stage] = report

        failing_gate = self.artifact("candidate-av-gate.json", json.dumps({
            "schema": "swainwong.candidate-av-gate.v1",
            "stage": "candidate-internal-gate",
            "candidate": {"sha256": candidate_sha, "duration_seconds": 1.0},
            "producer_id": "07-editing-producer",
            "review_reports": {
                stage: hashlib.sha256(path.read_bytes()).hexdigest()
                for stage, path in review_files.items()
            },
            "review": {
                "visual": {"status": "PASS", "coverage_seconds": 1.0, "reviewer": "10-visual-review-independent", "method": "continuous-normal-speed-final-file-review"},
                "audio": {"status": "PASS", "coverage_seconds": 1.0, "reviewer": "09-director-review-independent", "method": "continuous-normal-speed-final-file-review"},
            },
            "checks": {
                "visual_asset_policy": "PASS",
                "subtitle_single_authority": "PASS",
                "voice_pacing": "PASS",
                "animation_sfx_audible": "FAIL",
                "bgm_audible": "PASS",
                "chapter_navigation": "PASS",
                "source_quality": "PASS",
                "third_party_origin_uniqueness": "PASS",
                "chapter_labels_and_segmentation_visual": "PASS",
                "brand_overlay_visual": "PASS",
                "source_perceived_quality": "PASS",
                "short_shot_readability": "PASS",
                "source_semantic_fit": "PASS",
                "event_date_scope": "PASS",
                "claim_visual_alignment": "PASS",
            },
            "findings": ["SFX is inaudible in the context mix"],
        }))
        with self.assertRaisesRegex(ValueError, "animation_sfx_audible"):
            workflow_state.record_stage(
                self.project,
                "candidate-internal-gate",
                "READY",
                [failing_gate],
                evidence="final candidate reviewed",
            )

        passing = json.loads(failing_gate.read_text(encoding="utf-8"))
        passing["checks"]["animation_sfx_audible"] = "PASS"
        passing["findings"] = []
        passing_gate = self.artifact("candidate-av-gate-pass.json", json.dumps(passing))
        state = workflow_state.record_stage(
            self.project,
            "candidate-internal-gate",
            "READY",
            [passing_gate],
            evidence="hash-bound final candidate watched and listened at normal speed",
        )
        self.assertEqual(state["stages"]["candidate-internal-gate"]["status"], "READY")

        readiness = self.artifact("owner-review-ready.json", json.dumps({
            "schema": "swainwong.owner-review-ready.v1",
            "candidate_sha256": candidate_sha,
            "candidate_internal_gate_sha256": hashlib.sha256(passing_gate.read_bytes()).hexdigest(),
        }))
        state = workflow_state.record_stage(
            self.project,
            "owner-review-ready",
            "READY",
            [readiness],
            evidence="internal machine and independent review gates passed for this exact candidate",
        )
        self.assertEqual(state["stages"]["owner-review-ready"]["status"], "READY")


if __name__ == "__main__":
    unittest.main()
