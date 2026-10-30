# SwainWong Video Factory Codex Plugin Architecture

## Goal

Turn the existing `swainwong-video-workflow` skill into the single public entry point of a local, installable Codex plugin while keeping twelve role modules internal. Move deterministic gates into code and expose persistent workflow and feedback operations through a local MCP server.

## Product boundary

- The plugin is named `swainwong-video-factory`.
- The plugin exposes exactly one public skill: `swainwong-video-workflow`.
- The twelve production and review roles remain supporting Markdown modules; they must not contain `SKILL.md` or user-facing invocation metadata.
- Creative decisions remain in prompts and independent human/model review.
- Machine-checkable invariants are enforced by scripts or MCP tools, never by prose alone.
- The existing review page, immutable snapshots, media evidence, feedback analysis, and promotion contracts remain authoritative and must be packaged without weakening their status semantics.

## Deterministic contract

The runtime must enforce:

1. A production brief cannot lock unless its required fields are present and `brief_confirmed` is true.
2. Every workflow state is bound to a canonical brief SHA-256.
3. A stage cannot become `READY` unless every dependency is `READY`, every declared artifact exists, and its SHA-256 is recorded.
4. Review stages bind their decision to a target artifact SHA-256; changing that target invalidates the review and its downstream stages.
5. State changes append immutable event records rather than overwriting the historical meaning of earlier events.
6. Role task packets contain the role method, role Harness, brief identity, dependency artifacts, required evidence, and allowed result states.
7. Feedback analysis and promotion preserve the existing immutable-snapshot, evidence, independent-review, conflict-resolution, and exact-scope requirements.

## Prompt-owned decisions

The model and specialist roles decide narrative angle, wording, composition, visual metaphor, asset choice, motion design, voice performance, music, and qualitative audiovisual judgments. Code verifies that the decision and its evidence exist and are version-bound; code does not claim creative acceptance.

## Plugin package

The source package lives at `plugins/swainwong-video-factory/` and uses the portable Agent Plugins root manifest. It contains one skill, one local stdio MCP server, validation scripts, tests, and the existing video-review assets and scripts.

The `~/.codex/skills/swainwong-video-workflow` installation is a compatibility symlink to the canonical plugin skill. The local plugin is also installed and enabled. The compatibility link and plugin-prefixed Skill may therefore both appear in discovery; they are two access paths to the same maintained Skill, not two independent products. The compatibility link must not create a second editable source of truth.

## Maintenance and installed copies

Verified on 2026-10-30:

| Location | Role | Editing rule |
|---|---|---|
| `plugins/swainwong-video-factory/` | Canonical local plugin source: one Skill, references, assets, Python gates, MCP server, tests | All maintained changes start here |
| `~/.codex/skills/swainwong-video-workflow` | Symlink to the canonical plugin's `skills/swainwong-video-workflow` | Same source; changes are immediately visible through this path |
| `~/.codex/plugins/cache/swainwong-video-local/swainwong-video-factory/<version>/` | Installed versioned plugin snapshot | Refresh from source through the plugin installer; do not maintain a parallel fork here |
| `projects/.../h01-r5/`, `r5-native/` | Concrete video project, copied/customized render code and assets | Project changes are not automatically library changes; promote only reviewed reusable behavior |

Before this revision, source and the installed `0.3.8` snapshot matched across all 105 package files (excluding Python bytecode and `.DS_Store`). There was no code divergence. H01/D01 lessons are released in plugin `0.3.9`; the mechanical workflow contract remains `4.9`. These version numbers describe different layers, not separate tools. This update changes creative contracts and package metadata, not gate behavior or the generic title-renderer API.

For a local update: edit the canonical package, run the package tests and Skill validation, then use `codex plugin add swainwong-video-factory@swainwong-video-local --json` with the locally verified CLI. Recheck `codex plugin list --marketplace swainwong-video-local --json` and compare installed files to source. Keep task evidence outside the package. Existing conversations or Python server processes may retain loaded content; installation is not proof that a running process hot-reloaded. Start a new conversation to discover the updated plugin path when needed.

## Smoke-test boundary

Before producing a real video, an architecture smoke test must prove:

- plugin manifest and single-skill discovery;
- brief validation and locking;
- dependency gating and role task-packet generation;
- artifact hashing and stale-review invalidation;
- MCP initialization, tool discovery, state reads/writes, and feedback tool routing;
- preservation of the existing feedback Harness tests;
- no claim of visual, listening, or user acceptance from these technical checks.
