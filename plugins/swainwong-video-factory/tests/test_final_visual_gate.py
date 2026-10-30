import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = PLUGIN_ROOT / "skills" / "swainwong-video-workflow" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import final_visual_gate  # noqa: E402


def valid_manifest():
    return {
        "schema": "swainwong.final-visual-gate-input.v2",
        "candidate": {
            "path": "/tmp/candidate.mp4",
            "sha256": "a" * 64,
            "duration_seconds": 100.0,
            "width": 1920,
            "height": 1080,
        },
        "chapter_navigation": {
            "track": "single-full-width-segmented-navigation",
            "rendered_segment_count": 2,
            "rendered_separator_count": 1,
            "rendered_labels": ["问题", "机制"],
            "pixel_tolerance": 2.0,
            "chapters": [
                {
                    "label": "问题",
                    "start_seconds": 0.0,
                    "end_seconds": 40.0,
                    "rendered_start_x": 0.0,
                    "rendered_end_x": 768.0,
                },
                {
                    "label": "机制",
                    "start_seconds": 40.0,
                    "end_seconds": 100.0,
                    "rendered_start_x": 768.0,
                    "rendered_end_x": 1920.0,
                },
            ],
            "pixel_samples": [
                {"time_seconds": 0.0, "fill_x": 0.0},
                {"time_seconds": 20.0, "fill_x": 384.0},
                {"time_seconds": 39.9, "fill_x": 766.08},
                {"time_seconds": 40.0, "fill_x": 768.0},
                {"time_seconds": 40.1, "fill_x": 769.92},
                {"time_seconds": 70.0, "fill_x": 1344.0},
                {"time_seconds": 100.0, "fill_x": 1920.0},
            ],
        },
        "third_party_video_uses": [
            {
                "clip_id": "A1",
                "origin_id": "origin-a",
                "timeline_start": 0.0,
                "timeline_end": 4.0,
                "source_path": "/tmp/a.mp4",
                "source_sha256": hashlib.sha256(b"/tmp/a.mp4").hexdigest(),
                "source_in": 0.0,
                "source_out": 4.0,
                "source_width": 1920,
                "source_height": 1080,
                "render_width": 1920,
                "render_height": 1080,
                "zoom": 1.0,
                "composition_mode": "cover_full_frame",
            },
            {
                "clip_id": "B1",
                "origin_id": "origin-b",
                "timeline_start": 4.0,
                "timeline_end": 8.0,
                "source_path": "/tmp/b.mp4",
                "source_sha256": hashlib.sha256(b"/tmp/b.mp4").hexdigest(),
                "source_in": 0.0,
                "source_out": 4.0,
                "source_width": 1280,
                "source_height": 720,
                "render_width": 1920,
                "render_height": 1080,
                "zoom": 1.0,
                "composition_mode": "cover_full_frame",
            },
        ],
        "quality_policy": {
            "max_full_frame_linear_upscale": 1.5,
            "max_foreground_linear_upscale": 1.5,
        },
        "coverage_policy": {"third_party_primary_min_ratio": 0.08, "third_party_internal_video_min_ratio": 0.7},
        "third_party_image_uses": [],
        "visual_policy": {
            "forbidden_primary_types": ["code-vector", "generic-vector-illustration"],
            "minimum_readable_text_seconds": 1.5,
            "required_logo_anchor": "lower-right",
        },
        "subtitle_policy": {
            "authority": "openfilm-final-burn-in",
            "expected_languages": ["zh", "en"],
            "minimum_pixel_proofs": 3,
        },
        "subtitle_pixel_proofs": [
            {"cue_id": "S001", "time_seconds": 10.0, "clean_reference_path": "/tmp/clean-10.png", "clean_reference_sha256": "1" * 64, "region": {"x": 100, "y": 700, "width": 1720, "height": 300}},
            {"cue_id": "S002", "time_seconds": 50.0, "clean_reference_path": "/tmp/clean-50.png", "clean_reference_sha256": "2" * 64, "region": {"x": 100, "y": 700, "width": 1720, "height": 300}},
            {"cue_id": "S003", "time_seconds": 90.0, "clean_reference_path": "/tmp/clean-90.png", "clean_reference_sha256": "3" * 64, "region": {"x": 100, "y": 700, "width": 1720, "height": 300}},
        ],
        "audience_visual_units": [
            {
                "unit_id": "A1",
                "start_seconds": 0.0,
                "end_seconds": 4.0,
                "primary_type": "third-party-footage",
                "contains_readable_text": False,
                "sentence_ids": ["S001"], "claim_ids": ["C001"], "fact_source_ids": ["SRC001"], "evidence_overlay_origin_ids": ["official-page::SRC001"], "visible_evidence": [{"claim_id": "C001", "fact_source_id": "SRC001", "locator_or_crop": "paragraph 2, number and eight-day qualifier", "date_scope": "2025 dual holiday", "on_screen_start_seconds": 0.5, "on_screen_end_seconds": 3.5}], "event_date_scope": "2025 holiday", "semantic_status": "direct_evidence",
            },
            {
                "unit_id": "B1",
                "start_seconds": 4.0,
                "end_seconds": 8.0,
                "primary_type": "third-party-footage",
                "contains_readable_text": False,
                "sentence_ids": ["S002"], "claim_ids": [], "fact_source_ids": [], "event_date_scope": "current context", "semantic_status": "contextual",
            },
            {
                "unit_id": "N1",
                "start_seconds": 8.0,
                "end_seconds": 100.0,
                "primary_type": "original-raster-animation",
                "contains_readable_text": False,
                "sentence_ids": ["S003"], "claim_ids": [], "fact_source_ids": [], "event_date_scope": "not applicable", "semantic_status": "original_explanation",
            },
        ],
        "brand_overlay": {"anchor": "lower-right", "transparent": True, "backing_plate": False},
    }


def validate(manifest, *, source_overrides=None, candidate_overrides=None):
    candidate = manifest["candidate"]
    candidate_facts = {
        "path": candidate["path"],
        "sha256": candidate["sha256"],
        "duration_seconds": candidate["duration_seconds"],
        "width": candidate["width"],
        "height": candidate["height"],
        **(candidate_overrides or {}),
    }
    source_facts = {
        use["source_path"]: {
            "width": use["source_width"],
            "height": use["source_height"],
            "sha256": use["source_sha256"],
            "bit_rate": 2_000_000,
            "frame_rate": 30.0,
        }
        for use in manifest["third_party_video_uses"]
    }
    source_facts.update(source_overrides or {})
    navigation = manifest["chapter_navigation"]
    rendered_labels = navigation.get("rendered_labels", [])
    pixel_facts = {
        "samples": navigation.get("pixel_samples", []),
        "labels": [
            {"label": chapter["label"], "visible": chapter["label"] in rendered_labels}
            for chapter in navigation["chapters"]
        ],
        "separators": [
            {"visible": index < navigation.get("rendered_separator_count", 0)}
            for index in range(len(navigation["chapters"]) - 1)
        ],
    }
    appearance_facts = {
        use["clip_id"]: {"present": True, "orb_good_matches": 20}
        for use in [*manifest["third_party_video_uses"], *manifest.get("third_party_image_uses", [])]
    }
    subtitle_pixel_facts = {
        proof["cue_id"]: {"present": True, "detected_line_bands": 2, "changed_fraction": 0.02}
        for proof in manifest.get("subtitle_pixel_proofs", [])
    }
    return final_visual_gate.validate_manifest(
        manifest,
        candidate_facts=candidate_facts,
        source_facts=source_facts,
        pixel_facts=pixel_facts,
        appearance_facts=appearance_facts,
        subtitle_pixel_facts=subtitle_pixel_facts,
    )


class FinalVisualGateTests(unittest.TestCase):
    def test_rejects_non_contiguous_reuse_of_same_origin(self):
        manifest = valid_manifest()
        manifest["third_party_video_uses"].append({
            **manifest["third_party_video_uses"][0],
            "clip_id": "A2",
            "timeline_start": 8.0,
            "timeline_end": 12.0,
            "source_in": 8.0,
            "source_out": 12.0,
        })
        result = validate(manifest)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("third_party_origin_uniqueness", result["failed_checks"])
        self.assertEqual(result["checks"]["third_party_origin_uniqueness"]["origin-a"]["continuous_segments"], 2)

    def test_rejects_same_source_identity_disguised_as_two_origins(self):
        manifest = valid_manifest()
        manifest["third_party_video_uses"][1].update({
            "source_path": manifest["third_party_video_uses"][0]["source_path"],
            "source_sha256": manifest["third_party_video_uses"][0]["source_sha256"],
            "source_width": manifest["third_party_video_uses"][0]["source_width"],
            "source_height": manifest["third_party_video_uses"][0]["source_height"],
        })
        result = validate(manifest)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["checks"]["third_party_origin_uniqueness"]["__source_identity__"]["status"], "FAIL")

    def test_allows_adjacent_clips_from_one_origin_as_one_continuous_segment(self):
        manifest = valid_manifest()
        manifest["third_party_video_uses"].insert(1, {
            **manifest["third_party_video_uses"][0],
            "clip_id": "A2",
            "timeline_start": 4.0,
            "timeline_end": 6.0,
            "source_in": 4.0,
            "source_out": 6.0,
        })
        manifest["third_party_video_uses"][2]["timeline_start"] = 6.0
        manifest["third_party_video_uses"][2]["timeline_end"] = 10.0
        manifest["audience_visual_units"] = [
            manifest["audience_visual_units"][0],
            {"unit_id": "A2", "start_seconds": 4.0, "end_seconds": 6.0, "primary_type": "third-party-footage", "contains_readable_text": False, "sentence_ids": ["S001"], "claim_ids": [], "fact_source_ids": [], "event_date_scope": "current context", "semantic_status": "contextual"},
            {"unit_id": "B1", "start_seconds": 6.0, "end_seconds": 10.0, "primary_type": "third-party-footage", "contains_readable_text": False, "sentence_ids": ["S002"], "claim_ids": [], "fact_source_ids": [], "event_date_scope": "current context", "semantic_status": "contextual"},
            {"unit_id": "N1", "start_seconds": 10.0, "end_seconds": 100.0, "primary_type": "original-raster-animation", "contains_readable_text": False, "sentence_ids": ["S003"], "claim_ids": [], "fact_source_ids": [], "event_date_scope": "not applicable", "semantic_status": "original_explanation"},
        ]
        result = validate(manifest)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["checks"]["third_party_origin_uniqueness"]["origin-a"]["continuous_segments"], 1)

    def test_rejects_zoom_aware_full_frame_upscale_over_policy(self):
        manifest = valid_manifest()
        manifest["third_party_video_uses"][0].update({
            "source_width": 360,
            "source_height": 640,
            "zoom": 1.15,
        })
        result = validate(manifest)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("source_quality", result["failed_checks"])
        offender = result["checks"]["source_quality"]["offenders"][0]
        self.assertEqual(offender["clip_id"], "A1")
        self.assertGreater(offender["linear_upscale"], 6.0)

    def test_rejects_implausibly_low_bitrate_source(self):
        manifest = valid_manifest()
        path = manifest["third_party_video_uses"][0]["source_path"]
        result = validate(manifest, source_overrides={path: {
            "width": 1920,
            "height": 1080,
            "sha256": manifest["third_party_video_uses"][0]["source_sha256"],
            "bit_rate": 1,
            "frame_rate": 30.0,
        }})
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("source_quality", result["failed_checks"])

    def test_blurred_background_does_not_excuse_over_scaled_foreground(self):
        manifest = valid_manifest()
        manifest["third_party_video_uses"][0].update({
            "source_width": 360,
            "source_height": 640,
            "render_width": 900,
            "render_height": 1080,
            "zoom": 1.4,
            "composition_mode": "blurred_background_with_clear_foreground",
        })
        result = validate(manifest)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("source_quality", result["failed_checks"])

    def test_rejects_single_global_bar_without_rendered_segments(self):
        manifest = valid_manifest()
        navigation = manifest["chapter_navigation"]
        navigation["rendered_segment_count"] = 1
        navigation["rendered_separator_count"] = 0
        navigation["rendered_labels"] = ["问题"]
        result = validate(manifest)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("chapter_navigation_structure", result["failed_checks"])

    def test_rejects_progress_jump_at_chapter_boundary(self):
        manifest = valid_manifest()
        manifest["chapter_navigation"]["pixel_samples"][3]["fill_x"] = 1200.0
        result = validate(manifest)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("chapter_navigation_pixel_progress", result["failed_checks"])

    def test_rejects_forbidden_vector_primary_content(self):
        manifest = valid_manifest()
        manifest["audience_visual_units"][0]["primary_type"] = "code-vector"
        result = validate(manifest)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("visual_asset_policy", result["failed_checks"])

    def test_forbidden_primary_type_matching_is_case_insensitive(self):
        manifest = valid_manifest()
        manifest["audience_visual_units"][2]["primary_type"] = "SVG"
        result = validate(manifest)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("visual_asset_policy", result["failed_checks"])

    def test_rejects_unreadable_flash_card_even_between_fixed_interval_samples(self):
        manifest = valid_manifest()
        manifest["audience_visual_units"][0].update({
            "primary_type": "typographic-page",
            "contains_readable_text": True,
            "start_seconds": 104.35,
            "end_seconds": 104.65,
        })
        result = validate(manifest)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("readable_visual_duration", result["failed_checks"])
        self.assertEqual(result["checks"]["readable_visual_duration"]["offenders"][0]["unit_id"], "A1")

    def test_rejects_logo_in_wrong_corner_or_with_backing_plate(self):
        manifest = valid_manifest()
        manifest["brand_overlay"].update({"anchor": "upper-right", "backing_plate": True})
        result = validate(manifest)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("brand_overlay", result["failed_checks"])

    def test_valid_manifest_passes_all_checks(self):
        result = validate(valid_manifest())
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["failed_checks"], [])
        self.assertTrue(all(item["status"] == "PASS" for item in result["summary"].values()))

    def test_policy_thresholds_cannot_be_relaxed_by_manifest(self):
        manifest = valid_manifest()
        manifest["chapter_navigation"]["pixel_tolerance"] = 10000
        manifest["chapter_navigation"]["chapters"][0]["rendered_end_x"] = 1200
        manifest["quality_policy"] = {"max_full_frame_linear_upscale": 10000, "max_foreground_linear_upscale": 10000}
        manifest["visual_policy"] = {
            "forbidden_primary_types": [],
            "minimum_readable_text_seconds": 0.001,
            "required_logo_anchor": "upper-right",
        }
        manifest["third_party_video_uses"][0].update({"source_width": 1, "source_height": 1})
        manifest["audience_visual_units"][2].update({
            "primary_type": "code-vector-as-primary-content",
            "contains_readable_text": True,
            "start_seconds": 8.0,
            "end_seconds": 8.01,
        })
        manifest["audience_visual_units"].append({
            "unit_id": "N2",
            "start_seconds": 8.01,
            "end_seconds": 100.0,
            "primary_type": "original-raster-animation",
            "contains_readable_text": False,
            "sentence_ids": ["S003"], "claim_ids": [], "fact_source_ids": [], "event_date_scope": "not applicable", "semantic_status": "original_explanation",
        })
        manifest["brand_overlay"] = {"anchor": "upper-right", "transparent": True, "backing_plate": False}
        result = validate(manifest)
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue({"chapter_navigation_structure", "source_quality", "visual_asset_policy", "readable_visual_duration", "brand_overlay"}.issubset(result["failed_checks"]))

    def test_rejects_incomplete_visual_timeline_and_missing_source_probe(self):
        manifest = valid_manifest()
        manifest["audience_visual_units"] = manifest["audience_visual_units"][:2]
        source_facts = {
            manifest["third_party_video_uses"][0]["source_path"]: {
                "width": manifest["third_party_video_uses"][0]["source_width"],
                "height": manifest["third_party_video_uses"][0]["source_height"],
                "sha256": manifest["third_party_video_uses"][0]["source_sha256"],
                "bit_rate": 2_000_000,
                "frame_rate": 30.0,
            }
        }
        with self.assertRaisesRegex(ValueError, "source media facts missing"):
            final_visual_gate.validate_manifest(
                manifest,
                candidate_facts={
                    "path": manifest["candidate"]["path"],
                    "sha256": manifest["candidate"]["sha256"],
                    "duration_seconds": 100.0,
                    "width": 1920,
                    "height": 1080,
                },
                source_facts=source_facts,
                pixel_facts={"samples": [], "labels": [], "separators": []},
            )

    def test_rejects_missing_or_direct_mismatch_semantic_mapping(self):
        manifest = valid_manifest()
        manifest["audience_visual_units"][0]["semantic_status"] = "direct_mismatch"
        manifest["audience_visual_units"][1].pop("sentence_ids")
        result = validate(manifest)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("visual_semantic_contract", result["failed_checks"])

    def test_accepts_structured_event_date_scope(self):
        manifest = valid_manifest()
        manifest["audience_visual_units"][0]["event_date_scope"] = {
            "visual_event_scope": "store photo dated 2024-07-03",
            "fact_event_scope": "2025 dual holiday, eight days",
            "scope_limit": "photo proves identity only",
        }
        self.assertEqual(validate(manifest)["status"], "PASS")

    def test_accepts_structured_visible_evidence_locator_and_date_scope(self):
        manifest = valid_manifest()
        manifest["audience_visual_units"][0]["visible_evidence"][0]["locator_or_crop"] = {
            "source_locator": "opened text lines 1-8",
            "crop_rule": "retain publisher, date and all limiting words",
        }
        manifest["audience_visual_units"][0]["visible_evidence"][0]["date_scope"] = {
            "event_date": "2025 dual holiday, eight days",
            "published_date": "2025-10-09",
        }
        self.assertEqual(validate(manifest)["status"], "PASS")

    def test_rejects_reused_fact_page_crop_as_two_evidence_origins(self):
        manifest = valid_manifest()
        manifest["audience_visual_units"][1].update({
            "semantic_status": "direct_evidence",
            "claim_ids": ["C002"],
            "fact_source_ids": ["SRC001"],
            "evidence_overlay_origin_ids": ["official-page::SRC001"],
            "visible_evidence": [{"claim_id": "C002", "fact_source_id": "SRC001", "locator_or_crop": "paragraph 3", "date_scope": "2025", "on_screen_start_seconds": 4.5, "on_screen_end_seconds": 7.5}],
        })
        result = validate(manifest)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("visual_semantic_contract", result["failed_checks"])
        self.assertTrue(any(issue["reason"] == "evidence_overlay_origin_reused" for issue in result["checks"]["visual_semantic_contract"]["issues"]))

    def test_rejects_direct_evidence_without_exact_visible_locator_mapping(self):
        manifest = valid_manifest()
        manifest["audience_visual_units"][0]["visible_evidence"] = []
        result = validate(manifest)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("visual_semantic_contract", result["failed_checks"])

    def test_rejects_third_party_or_internal_video_ratio_below_locked_minimum(self):
        manifest = valid_manifest()
        manifest["coverage_policy"] = {"third_party_primary_min_ratio": 0.7, "third_party_internal_video_min_ratio": 0.7}
        result = validate(manifest)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("third_party_coverage", result["failed_checks"])
        self.assertAlmostEqual(result["checks"]["third_party_coverage"]["third_party_primary_ratio"], 0.08)

    def test_rejects_missing_final_pixel_subtitle_proof(self):
        manifest = valid_manifest()
        manifest["subtitle_pixel_proofs"] = manifest["subtitle_pixel_proofs"][:2]
        result = validate(manifest)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("subtitle_pixel_presence", result["failed_checks"])

    def test_rejects_no_subtitle_pixels_at_a_declared_cue(self):
        manifest = valid_manifest()
        candidate = manifest["candidate"]
        candidate_facts = {"path": candidate["path"], "sha256": candidate["sha256"], "duration_seconds": 100.0, "width": 1920, "height": 1080}
        source_facts = {
            use["source_path"]: {"width": use["source_width"], "height": use["source_height"], "sha256": use["source_sha256"], "bit_rate": 2_000_000, "frame_rate": 30.0}
            for use in manifest["third_party_video_uses"]
        }
        pixel_facts = {"samples": manifest["chapter_navigation"]["pixel_samples"], "labels": [{"label": "问题", "visible": True}, {"label": "机制", "visible": True}], "separators": [{"visible": True}]}
        appearance_facts = {use["clip_id"]: {"present": True} for use in manifest["third_party_video_uses"]}
        subtitle_facts = {proof["cue_id"]: {"present": proof["cue_id"] != "S002", "detected_line_bands": 0 if proof["cue_id"] == "S002" else 2, "changed_fraction": 0.0 if proof["cue_id"] == "S002" else 0.02} for proof in manifest["subtitle_pixel_proofs"]}
        result = final_visual_gate.validate_manifest(manifest, candidate_facts=candidate_facts, source_facts=source_facts, pixel_facts=pixel_facts, appearance_facts=appearance_facts, subtitle_pixel_facts=subtitle_facts)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("subtitle_pixel_presence", result["failed_checks"])

    def test_image_identity_is_recomputed_from_regular_file(self):
        manifest = valid_manifest()
        with tempfile.TemporaryDirectory() as folder:
            image = Path(folder) / "same.jpg"
            image.write_bytes(b"real-image-identity")
            digest = hashlib.sha256(image.read_bytes()).hexdigest()
            manifest["third_party_image_uses"] = [
                {"clip_id": "I1", "origin_id": "image-a", "source_path": str(image), "source_sha256": digest, "timeline_start": 8.0, "timeline_end": 9.0},
                {"clip_id": "I2", "origin_id": "image-b", "source_path": str(image), "source_sha256": digest, "timeline_start": 9.0, "timeline_end": 10.0},
            ]
            result = validate(manifest)
            self.assertEqual(result["status"], "FAIL")
            self.assertIn("third_party_image_uniqueness", result["failed_checks"])

            manifest["third_party_image_uses"][0]["source_sha256"] = "0" * 64
            with self.assertRaisesRegex(ValueError, "sha256 does not match"):
                validate(manifest)


if __name__ == "__main__":
    unittest.main()
