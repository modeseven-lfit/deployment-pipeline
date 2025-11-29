#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""Extract .github content from cloned repositories to create skeleton."""

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any


def extract_github_content(
    source_dir: Path,
    output_dir: Path,
    prune_empty: bool = True,
) -> dict[str, Any]:
    """Extract .github directories from source to output.

    Args:
        source_dir: Root directory containing cloned repositories
        output_dir: Output directory for skeleton structure
        prune_empty: Remove repositories without .github content

    Returns:
        Dictionary with extraction statistics
    """
    stats: dict[str, Any] = {
        "total_repos": 0,
        "repos_with_github": 0,
        "repos_without_github": 0,
        "total_files": 0,
        "repositories": [],
    }

    if not source_dir.exists():
        raise FileNotFoundError(f"Source directory not found: {source_dir}")

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Walk through source directory structure
    # We need to find all git repositories
    for item in source_dir.rglob(".git"):
        if not item.is_dir():
            continue

        repo_path = item.parent
        relative_path = repo_path.relative_to(source_dir)
        stats["total_repos"] += 1

        # Check for .github directory
        github_dir = repo_path / ".github"
        if not github_dir.exists() or not github_dir.is_dir():
            stats["repos_without_github"] += 1
            repo_info_empty: dict[str, Any] = {
                "path": str(relative_path),
                "has_github": False,
                "files_copied": 0,
            }
            stats["repositories"].append(repo_info_empty)

            if not prune_empty:
                # Create empty directory structure
                target_repo_dir = output_dir / relative_path
                target_repo_dir.mkdir(parents=True, exist_ok=True)
                print(f"  Created empty: {relative_path} (no .github content)")
            else:
                print(f"  Skipped: {relative_path} (no .github content)")
            continue

        # Repository has .github content
        stats["repos_with_github"] += 1
        file_count = 0

        # Create target directory structure
        target_repo_dir = output_dir / relative_path
        target_github_dir = target_repo_dir / ".github"
        target_github_dir.mkdir(parents=True, exist_ok=True)

        # Copy .github directory contents recursively
        for github_item in github_dir.rglob("*"):
            if github_item.is_file():
                rel_to_github = github_item.relative_to(github_dir)
                target_file = target_github_dir / rel_to_github
                target_file.parent.mkdir(parents=True, exist_ok=True)

                shutil.copy2(github_item, target_file)
                file_count += 1
                stats["total_files"] += 1

        repo_info_with_github: dict[str, Any] = {
            "path": str(relative_path),
            "has_github": True,
            "files_copied": file_count,
        }
        stats["repositories"].append(repo_info_with_github)

        print(f"  Extracted: {relative_path} ({file_count} files in .github/)")

    return stats


def main() -> int:
    """Extract .github content from cloned repositories."""
    parser = argparse.ArgumentParser(
        description="Extract .github content to create skeleton structure"
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        required=True,
        help="Source directory containing cloned repositories",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Output directory for skeleton structure",
    )
    parser.add_argument(
        "--prune-empty",
        action="store_true",
        default=True,
        help="Prune repositories without .github content (default: true)",
    )
    parser.add_argument(
        "--no-prune-empty",
        action="store_false",
        dest="prune_empty",
        help="Keep repositories without .github content",
    )
    parser.add_argument(
        "--stats-file",
        type=Path,
        help="Output file for extraction statistics (JSON)",
    )

    args = parser.parse_args()

    print(f"Extracting .github content from: {args.source_dir}")
    print(f"Output directory: {args.output_dir}")
    print(f"Prune empty repositories: {args.prune_empty}")
    print()

    try:
        stats = extract_github_content(
            source_dir=args.source_dir,
            output_dir=args.output_dir,
            prune_empty=args.prune_empty,
        )

        print()
        print("=" * 60)
        print("Extraction Statistics:")
        print(f"  Total repositories: {stats['total_repos']}")
        print(f"  Repositories with .github: {stats['repos_with_github']}")
        print(f"  Repositories without .github: {stats['repos_without_github']}")
        print(f"  Total files copied: {stats['total_files']}")
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
