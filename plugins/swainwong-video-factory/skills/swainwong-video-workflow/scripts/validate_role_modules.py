#!/usr/bin/env python3
"""Validate nested role modules, rule IDs, links, and non-discoverability."""
from __future__ import annotations

import argparse
import re
from pathlib import Path

from generate_role_modules import ROLES, role_folder_name


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--workflow-root",
        type=Path,
        default=Path.home() / ".codex" / "skills" / "swainwong-video-workflow",
    )
    args = parser.parse_args()
    root = args.workflow_root.resolve()
    errors: list[str] = []
    seen_roles: set[str] = set()
    link_sources = [root / "SKILL.md", root / "harness" / "HARNESS.md", root / "roles" / "INDEX.md"]
    for path in link_sources:
        if not path.is_file():
            errors.append(f"missing {path}")
    for role in ROLES:
        name = role_folder_name(role)
        folder = root / "roles" / name
        required = [folder / "METHOD.md", folder / "HARNESS.md"]
        for path in required:
            if not path.is_file():
                errors.append(f"missing {path}")
        if any(not path.is_file() for path in required):
            continue
        method = required[0].read_text(encoding="utf-8")
        harness = required[1].read_text(encoding="utf-8")
        if method.startswith("---") or (folder / "SKILL.md").exists() or (folder / "agents" / "openai.yaml").exists():
            errors.append(f"discoverable skill metadata must not exist in {folder}")
        if name in seen_roles:
            errors.append(f"duplicate role {name}")
        seen_roles.add(name)
        must = re.findall(rf"^\| {role['code']}-M(\d\d) \|", harness, re.M)
        forbidden = re.findall(rf"^\| {role['code']}-F(\d\d) \|", harness, re.M)
        if len(must) != len(role["must"]) or len(set(must)) != len(must):
            errors.append(f"MUST IDs invalid {name}")
        if len(forbidden) != len(role["forbidden"]) or len(set(forbidden)) != len(forbidden):
            errors.append(f"FORBIDDEN IDs invalid {name}")
        link_sources.extend(required)
    for source in link_sources:
        if not source.is_file():
            continue
        for link in re.findall(r"\]\(([^)]+)\)", source.read_text(encoding="utf-8")):
            if link.startswith(("http://", "https://", "#")):
                continue
            target = Path(link)
            if not target.is_absolute():
                target = source.parent / target
            if not target.resolve().exists():
                errors.append(f"broken link {source}: {link}")
    nested_skills = list((root / "roles").rglob("SKILL.md"))
    nested_agents = list((root / "roles").rglob("openai.yaml"))
    if nested_skills or nested_agents:
        errors.append("role modules expose skill metadata: " + ", ".join(map(str, nested_skills + nested_agents)))
    top_level = [
        root.parent / f"swainwong-video-{role['slug']}"
        for role in ROLES
        if (root.parent / f"swainwong-video-{role['slug']}").exists()
    ]
    if top_level:
        errors.append("top-level role skills still exposed: " + ", ".join(map(str, top_level)))
    if len(seen_roles) != 12:
        errors.append(f"expected 12 role modules, found {len(seen_roles)}")
    if errors:
        raise SystemExit("\n".join(errors))
    print("OK: 12 nested role modules; non-discoverability, harness IDs, and local links verified")


if __name__ == "__main__":
    main()
