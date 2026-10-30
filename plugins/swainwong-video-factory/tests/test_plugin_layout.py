import json
from pathlib import Path
import unittest


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PLUGIN_ROOT.parents[1]


class PluginLayoutTests(unittest.TestCase):
    def test_portable_manifest_identifies_video_factory(self):
        manifest = json.loads((PLUGIN_ROOT / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["$schema"], "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json")
        self.assertEqual(manifest["name"], "swainwong-video-factory")
        self.assertEqual(manifest["version"], "0.3.10")
        self.assertTrue(manifest["extensions"]["com.openai"]["requires_local_executor"])

    def test_plugin_exposes_exactly_one_public_skill(self):
        skill_files = sorted(PLUGIN_ROOT.glob("skills/**/SKILL.md"))
        self.assertEqual(
            skill_files,
            [PLUGIN_ROOT / "skills" / "swainwong-video-workflow" / "SKILL.md"],
        )

    def test_all_twelve_roles_are_internal_modules(self):
        roles = PLUGIN_ROOT / "skills" / "swainwong-video-workflow" / "roles"
        role_dirs = sorted(path for path in roles.iterdir() if path.is_dir())
        self.assertEqual(len(role_dirs), 12)
        for role in role_dirs:
            self.assertTrue((role / "METHOD.md").is_file())
            self.assertTrue((role / "HARNESS.md").is_file())
            self.assertFalse((role / "SKILL.md").exists())
            self.assertFalse((role / "agents" / "openai.yaml").exists())

    def test_local_mcp_command_uses_plugin_root(self):
        config = json.loads((PLUGIN_ROOT / "mcp.json").read_text(encoding="utf-8"))
        server = config["mcpServers"]["swainwong-video-workflow"]
        self.assertEqual(server["type"], "stdio")
        self.assertEqual(server["command"], "python3")
        self.assertEqual(server["args"], ["${PLUGIN_ROOT}/server/workflow_mcp.py"])
        self.assertEqual(server["cwd"], "${PLUGIN_ROOT}")

    def test_repo_marketplace_points_to_plugin(self):
        marketplace = json.loads((REPO_ROOT / ".agents" / "plugins" / "marketplace.json").read_text(encoding="utf-8"))
        self.assertEqual(marketplace["name"], "swainwong-video-local")
        entry = next(item for item in marketplace["plugins"] if item["name"] == "swainwong-video-factory")
        self.assertEqual(entry["source"]["path"], "./plugins/swainwong-video-factory")
        self.assertEqual(entry["source"]["source"], "local")
        self.assertEqual((REPO_ROOT / entry["source"]["path"]).resolve(), PLUGIN_ROOT.resolve())

    def test_plugin_entrypoints_are_bundled_without_home_installation(self):
        # A fresh clone must not depend on the author's ~/.codex installation.
        self.assertTrue((PLUGIN_ROOT / "server" / "workflow_mcp.py").is_file())
        skill = PLUGIN_ROOT / "skills" / "swainwong-video-workflow"
        self.assertTrue((skill / "SKILL.md").is_file())
        self.assertTrue((skill / "scripts" / "workflow_state.py").is_file())

    def test_candidate_av_gate_is_routed_and_executable(self):
        skill = PLUGIN_ROOT / "skills" / "swainwong-video-workflow"
        contract = skill / "references" / "candidate-av-gate.md"
        self.assertTrue(contract.is_file())
        self.assertIn("candidate-av-gate.md", (skill / "SKILL.md").read_text(encoding="utf-8"))
        workflow = (skill / "scripts" / "workflow_state.py").read_text(encoding="utf-8")
        self.assertIn("swainwong.candidate-av-gate.v1", workflow)

    def test_first_full_cut_contract_is_routed_and_executable(self):
        skill = PLUGIN_ROOT / "skills" / "swainwong-video-workflow"
        contract = skill / "references" / "first-full-cut.md"
        self.assertTrue(contract.is_file())
        self.assertIn("first-full-cut.md", (skill / "SKILL.md").read_text(encoding="utf-8"))
        workflow = (skill / "scripts" / "workflow_state.py").read_text(encoding="utf-8")
        self.assertIn("swainwong.first-full-cut.v1", workflow)

    def test_editorial_gates_are_routed_and_executable(self):
        skill = PLUGIN_ROOT / "skills" / "swainwong-video-workflow"
        contract = skill / "references" / "editorial-style-and-subtitles.md"
        self.assertTrue(contract.is_file())
        self.assertIn("editorial-style-and-subtitles.md", (skill / "SKILL.md").read_text(encoding="utf-8"))
        self.assertTrue((skill / "scripts" / "script_style_gate.py").is_file())
        self.assertTrue((skill / "scripts" / "subtitle_phrase_gate.py").is_file())


if __name__ == "__main__":
    unittest.main()
