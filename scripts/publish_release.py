#!/usr/bin/env python3
"""
publish_release.py - cut a Replicate release: regenerate the clean hub, publish it to the public
storefront repo, tag it, and create a GitHub Release whose notes come from CHANGELOG.md - the
manual-decision, automatic-mechanics publish step (design\\portability.md, "Replicate distribution").

CHANGELOG.md (this repo's root) is the single master record of what's in each version - you write
a `## [X.Y.Z] - YYYY-MM-DD` section there yourself when you decide to release. This script never
writes changelog prose; it only reads the section for --version and does everything mechanical:

  1. Require a CHANGELOG.md section for --version (refuses to publish without one).
  2. Regenerate a clean hub via seed_hub.py (same allowlist/scrub/leak-scan as any Replicate copy).
  3. Sync it into the persistent local clone at config publish.public_repo_path (preserving .git).
  4. Commit, tag v<version>, push.
  5. `gh release create` with that CHANGELOG section as the notes body, attaching the zip.

Re-editing a past release's notes: fix the section in CHANGELOG.md, then re-run with --sync-notes -
it pushes the updated CHANGELOG.md into the public repo and re-syncs that release's notes on GitHub,
WITHOUT cutting a new version (no regenerate, no new tag).

OS-reach Tier 2 port of publish_release.ps1 (design\\portability.md, "OS-reach Tier 2: full
cross-platform design"). Logic is a direct translation - see that doc's Build order for the
parity-check approach used to verify ports in this series.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config_lib import get_shared_config

SHARED_ROOT = Path(__file__).resolve().parent.parent
MARKER_NAME = '_DO_NOT_EDIT_LOCAL_CLONE.md'


def write_utf8(path, content):
    # Python's utf-8 encoding never writes a BOM (unlike PS 5.1's -Encoding utf8); newline='\n'
    # keeps embedded '\n' as LF instead of Windows-translating it to CRLF on write.
    path.write_text(content, encoding='utf-8', newline='\n')


def make_notes_file(text):
    # mkstemp() returns an open fd as well as a path; unlike PS's GetTempFileName()+WriteAllText
    # (no open handle involved), that fd must be closed here or Windows refuses to unlink() the
    # file later (a handle still open in this same process blocks its own delete).
    fd, path = tempfile.mkstemp()
    os.close(fd)
    path = Path(path)
    write_utf8(path, text)
    return path


def get_changelog_section(changelog_path, ver):
    if not changelog_path.exists():
        raise RuntimeError(f"CHANGELOG.md not found at {changelog_path}.")
    text = changelog_path.read_text(encoding='utf-8')
    pattern = r'^## \[' + re.escape(ver) + r'\].*?(?=\n## \[|\Z)'
    m = re.search(pattern, text, re.MULTILINE | re.DOTALL)
    if not m:
        today = date.today().isoformat()
        raise RuntimeError(
            f"No '## [{ver}]' section found in CHANGELOG.md ({changelog_path}).\n"
            "Write the release notes there first, e.g.:\n\n"
            f"  ## [{ver}] - {today}\n"
            "  ### Added\n"
            "  - ...\n\n"
            "Then re-run this script."
        )
    return m.group(0).strip()


def get_owner_repo(remote_url):
    m = re.search(r'github\.com[:/]+([^/]+)/([^/.]+?)(\.git)?/?$', remote_url)
    if not m:
        raise RuntimeError(f"Could not parse owner/repo from publish.public_repo_remote ('{remote_url}').")
    return f"{m.group(1)}/{m.group(2)}"


def write_do_not_edit_marker(path):
    # Local-only reminder (gitignored via the KEEP'd .gitignore - never ships to the public repo).
    # Written/refreshed on every run so it survives the full-publish wipe below and is never stale.
    text = """# DO NOT EDIT FILES IN THIS FOLDER DIRECTLY

This is a local working clone that `publish_release.py` (in the private tower_crane hub) fully
manages. Every release overwrites everything here except this file and `.git`, regenerated fresh
from the source hub - manual edits anywhere else in this folder are silently discarded on the next
release.

To actually change something that ships:
- Most files (hooks, scripts, templates, CLAUDE.md, CHANGELOG.md) - edit them in the source
  tower_crane repo, commit, then run publish_release.py again.
- This folder's own README.md - it's regenerated, not copied; edit the `readme` string inside
  tower_crane\\scripts\\seed_hub.py instead.
- Release notes only (no new version) - edit tower_crane\\CHANGELOG.md, then run
  publish_release.py --version X.Y.Z --sync-notes.

Full reference: tower_crane\\README.md - "Publish a versioned release" / "What actually ships".
"""
    write_utf8(path / MARKER_NAME, text)


def main():
    parser = argparse.ArgumentParser(
        description="Cut a Replicate release: regenerate, publish to the public storefront repo, tag, and create a GitHub Release."
    )
    parser.add_argument('--version', required=True, help='The version to publish, e.g. "1.0.0" (no "v" prefix). Must match a `## [Version]` section in CHANGELOG.md.')
    parser.add_argument('--sync-notes', action='store_true', help="Re-sync CHANGELOG.md + that version's already-published GitHub Release notes, without cutting a new version.")
    args = parser.parse_args()
    version = args.version

    cfg = get_shared_config(SHARED_ROOT)
    publish = cfg.get('publish') or {}
    public_repo_path = str(publish.get('public_repo_path') or '')
    public_repo_remote = str(publish.get('public_repo_remote') or '')
    if (not public_repo_path.strip() or public_repo_path.startswith('<') or
            not public_repo_remote.strip() or public_repo_remote.startswith('<')):
        raise RuntimeError("config.local.json is missing 'publish.public_repo_path' / 'publish.public_repo_remote' (see config.example.json).")

    public_path = Path(public_repo_path)
    tag = f"v{version}"
    changelog_path = SHARED_ROOT / 'CHANGELOG.md'
    notes = get_changelog_section(changelog_path, version)
    owner_repo = get_owner_repo(public_repo_remote)

    if not shutil.which('gh'):
        raise RuntimeError("gh (GitHub CLI) not found on PATH.")

    # --- ensure the persistent local clone exists and is current -------------------------------------
    if not (public_path / '.git').exists():
        print(f"Cloning public repo to {public_path} ...")
        subprocess.run(['git', 'clone', public_repo_remote, str(public_path)], check=True)
    else:
        print(f"Syncing local clone ({public_path}) with origin ...")
        subprocess.run(['git', '-C', str(public_path), 'checkout', 'main'], check=True)
        subprocess.run(['git', '-C', str(public_path), 'pull', '--ff-only', 'origin', 'main'], check=True)
    write_do_not_edit_marker(public_path)

    if args.sync_notes:
        # --- notes-only sync: push the corrected CHANGELOG.md + re-sync that release's notes ---------
        existing = subprocess.run(['gh', 'release', 'view', tag, '-R', owner_repo], capture_output=True, text=True)
        if existing.returncode != 0:
            raise RuntimeError(f"No published release '{tag}' on {owner_repo} yet - run without --sync-notes to publish it first.")

        shutil.copy2(changelog_path, public_path / 'CHANGELOG.md')
        subprocess.run(['git', '-C', str(public_path), 'add', 'CHANGELOG.md'], check=True)
        changed = subprocess.run(['git', '-C', str(public_path), 'status', '--porcelain'], capture_output=True, text=True, check=True).stdout.strip()
        if changed:
            subprocess.run(['git', '-C', str(public_path), 'commit', '-m', 'Update CHANGELOG.md'], check=True)
            subprocess.run(['git', '-C', str(public_path), 'push', 'origin', 'main'], check=True)
            print("Pushed updated CHANGELOG.md to the public repo.")
        else:
            print("Public CHANGELOG.md already matches the master copy - nothing to push.")

        notes_file = make_notes_file(notes)
        try:
            subprocess.run(['gh', 'release', 'edit', tag, '-R', owner_repo, '--notes-file', str(notes_file)], check=True)
        finally:
            notes_file.unlink()
        print()
        print(f"Re-synced notes for {tag} on {owner_repo}.")
        return

    # --- full publish: refuse to redo an existing version -------------------------------------------
    local_tag = subprocess.run(['git', '-C', str(public_path), 'tag', '-l', tag], capture_output=True, text=True, check=True).stdout.strip()
    remote_tag = subprocess.run(['git', 'ls-remote', '--tags', public_repo_remote, f"refs/tags/{tag}"], capture_output=True, text=True, check=True).stdout.strip()
    if local_tag or remote_tag:
        raise RuntimeError(f"Tag '{tag}' already exists on the public repo. Bump --version, or use --sync-notes to just update its notes.")

    # --- regenerate the clean hub into a scratch dir, then sync into the persistent clone -----------
    scratch_parent = Path(tempfile.gettempdir()) / f"tower_crane_release_{uuid.uuid4().hex[:8]}"
    scratch_out = scratch_parent / 'hub'
    scratch_parent.mkdir(parents=True, exist_ok=True)
    try:
        seed_hub_script = Path(__file__).resolve().parent / 'seed_hub.py'
        result = subprocess.run(
            [sys.executable, str(seed_hub_script), '--out', str(scratch_out), '--zip', '--version', version],
            cwd=str(SHARED_ROOT),
        )
        if result.returncode != 0:
            raise RuntimeError(f"seed_hub.py failed (exit {result.returncode}).")
        zip_path = scratch_parent / f"tower-crane-{version}.zip"
        if not zip_path.exists():
            raise RuntimeError(f"Expected release zip not found at {zip_path}.")

        print()
        print(f"Syncing generated hub into {public_path} (preserving .git) ...")
        for child in public_path.iterdir():
            if child.name == '.git':
                continue
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
        shutil.copytree(scratch_out, public_path, dirs_exist_ok=True)
        write_do_not_edit_marker(public_path)

        subprocess.run(['git', '-C', str(public_path), 'add', '-A'], check=True)
        changed = subprocess.run(['git', '-C', str(public_path), 'status', '--porcelain'], capture_output=True, text=True, check=True).stdout.strip()
        if changed:
            subprocess.run(['git', '-C', str(public_path), 'commit', '-m', f"Release {tag}"], check=True)
        else:
            print(f"No file changes vs. current public HEAD - tagging current content as {tag}.")
        subprocess.run(['git', '-C', str(public_path), 'tag', tag], check=True)
        subprocess.run(['git', '-C', str(public_path), 'push', 'origin', 'main'], check=True)
        subprocess.run(['git', '-C', str(public_path), 'push', 'origin', tag], check=True)

        notes_file = make_notes_file(notes)
        try:
            subprocess.run(['gh', 'release', 'create', tag, '-R', owner_repo, '--title', tag, '--notes-file', str(notes_file), str(zip_path)], check=True)
        finally:
            notes_file.unlink()

        print()
        print(f"Published {tag} to {owner_repo}.")
        print(f"  Release: https://github.com/{owner_repo}/releases/tag/{tag}")
    finally:
        if scratch_parent.exists():
            shutil.rmtree(scratch_parent)


if __name__ == '__main__':
    main()
