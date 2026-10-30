# SwainWong Video Factory repository

This Git repository contains the video-production plugin, not the local video-production workspace that surrounds it.

- Maintain the sole source package at `plugins/swainwong-video-factory/`. Follow its `AGENTS.md` when changing the package.
- Keep the repository-root `.gitignore` allowlist. Do not force-add projects, downloaded/reference media, rendered videos, voice samples, credentials, local Codex configuration, or runtime state.
- Preserve the local compatibility symlink to the package Skill; never maintain a second editable copy in an installed cache.
- Keep tests runnable from a fresh clone. User-home installations and project-local `.codex/config.toml` are optional local state, not test prerequisites.
- Run `python3 -m unittest discover -s plugins/swainwong-video-factory/tests -v` and the standalone animal-motion gate fixtures before shipping package changes.
- Installation and machine checks do not establish visual, listening, or owner acceptance of any video.
