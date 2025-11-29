#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""Apply workflow-deployment overlays to target repositories."""

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any


def apply_overlay(
    overlay_dir: Path,
    target_dir: Path,
    project_slug: str,
) -> dict[str, Any]:
    """Apply workflow overlay to target repositories.

    Args:
        overlay_dir: Directory containing overlay structure
        target_dir: Target directory with repository structure
        project_slug: Project slug to match in overlay

    Returns:
        Dictionary with overlay statistics
    """
    stats: dict[str, Any] = {
        "overlay_dir": str(overlay_dir),
        "target_dir": str(target_dir),
        "project_slug": project_slug,
        "repos_updated": 0,
        "files_copied": 0,
        "files_overwritten": 0,
        "repositories": [],
    }

    if not overlay_dir.exists():
        raise FileNotFoundError(f"Overlay directory not found: {overlay_dir}")

    if not target_dir.exists():
        raise FileNotFoundError(f"Target directory not found: {target_dir}")

    # Look for project slug directory in overlay
    project_overlay_dir = overlay_dir / project_slug
    if not project_overlay_dir.exists():
        print(f"No overlay found for project slug '{project_slug}' in {overlay_dir}")
        return stats

    print(f"Found overlay for project: {project_slug}")

    # Walk through project overlay structure
    # Structure: overlay_dir/{slug}/{repo-name}/{files...}
    for repo_dir in project_overlay_dir.iterdir():
        if not repo_dir.is_dir():
            continue

        repo_name = repo_dir.name
        print(f"  Processing overlay for repository: {repo_name}")

        # Find matching repository in target (case-insensitive)
        target_repo_dir = None
        for target_item in target_dir.rglob(".git"):
            if not target_item.is_dir():
                continue

            candidate_repo = target_item.parent
            candidate_name = candidate_repo.name

            if candidate_name.lower() == repo_name.lower():
                target_repo_dir = candidate_repo
                break

        if not target_repo_dir:
            print(
                f"    WARNING: Repository '{repo_name}' not found in target directory"
            )
            repo_info_not_found: dict[str, Any] = {
                "name": repo_name,
                "status": "not_found",
                "files_copied": 0,
            }
            stats["repositories"].append(repo_info_not_found)
            continue

        # Apply overlay files
        files_copied = 0
        files_overwritten = 0

        for overlay_file in repo_dir.rglob("*"):
            if not overlay_file.is_file():
                continue

            # Get relative path from repo root
            rel_path = overlay_file.relative_to(repo_dir)
            target_file = target_repo_dir / rel_path

            # Track if file exists (will be overwritten)
            file_existed = target_file.exists()

            # Create parent directories
            target_file.parent.mkdir(parents=True, exist_ok=True)

            # Copy file (overwrite if exists)
            shutil.copy2(overlay_file, target_file)
            files_copied += 1

            if file_existed:
                files_overwritten += 1
                print(f"    Overwritten: {rel_path}")
            else:
                print(f"    Copied: {rel_path}")

        stats["repos_updated"] += 1
        stats["files_copied"] += files_copied
        stats["files_overwritten"] += files_overwritten

        repo_info_success: dict[str, Any] = {
            "name": repo_name,
            "status": "updated",
            "files_copied": files_copied,
            "files_overwritten": files_overwritten,
        }
        stats["repositories"].append(repo_info_success)

        print(f"    Applied {files_copied} files ({files_overwritten} overwritten)")

    return stats


def main() -> int:
    """Apply workflow overlays to target repositories."""
    parser = argparse.ArgumentParser(description="Apply workflow-deployment overlays")
    parser.add_argument(
        "--overlay-dir",
        type=Path,
        required=True,
        help="Directory containing workflow-deployment overlays",
    )
    parser.add_argument(
        "--target-dir",
        type=Path,
        required=True,
        help="Target directory with repository structure",
    )
    parser.add_argument(
        "--project-slug",
        type=str,
        required=True,
        help="Project slug to match in overlay structure",
    )
    parser.add_argument(
        "--stats-file",
        type=Path,
        help="Output file for overlay statistics (JSON)",
    )

    args = parser.parse_args()

    print(f"Applying overlays from: {args.overlay_dir}")
    print(f"Target directory: {args.target_dir}")
    print(f"Project slug: {args.project_slug}")
    print()

    try:
        stats = apply_overlay(
            overlay_dir=args.overlay_dir,
            target_dir=args.target_dir,
            project_slug=args.project_slug,
        )

        print()
        print("=" * 60)
        print("Overlay Statistics:")
        print(f"  Repositories updated: {stats['repos_updated']}")
        print(f"  Total files copied: {stats['files_copied']}")
        print(f"  Files overwritten: {stats['files_overwritten']}")
        print("=" * 60)

        # Write stats to file if requested
        if args.stats_file:
            args.stats_file.parent.mkdir(parents=True, exist_ok=True)
            args.stats_file.write_text(json.dumps(stats, indent=2))
            print(f"\nStatistics written to: {args.stats_file}")

        return 0

    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
