# SwainWong Video Factory plugin maintenance

This repository packages one public Codex Skill. Keep `skills/swainwong-video-workflow/SKILL.md` as the only discoverable `SKILL.md` in the plugin.

- Treat role `METHOD.md` and `HARNESS.md` files as internal task-packet resources, not user-facing Skills.
- Put qualitative and creative decisions in Markdown contracts; put mechanically decidable gates in tested Python.
- Preserve immutable hashes, status meanings, independent-review boundaries, and user-confirmed scope.
- A technical test, file hash, render, decode, screenshot, or MCP response does not establish creative visual or listening acceptance.
- Write a failing test before changing Python behavior. Run the full plugin test suite before reporting completion.
- Keep runtime state in the target video project. Do not write mutable workflow state into the installed plugin directory.
