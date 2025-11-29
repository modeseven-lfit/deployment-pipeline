#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""Push content to GitHub repositories."""

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any


def run_command(
    cmd: list[str],
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    capture_output: bool = True,
) -> tuple[int, str, str]:
    """Run shell command and return exit code, stdout, stderr."""
    result = subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        capture_output=capture_output,
        text=True,
    )
    return result.returncode, result.stdout, result.stderr


def setup_git_config() -> None:
    """Configure git user for commits."""
    run_command(["git", "config", "--global", "user.name", "GitHub Actions"])
    run_command(["git", "config", "--global", "user.email", "actions@github.com"])


def create_repo_if_needed(
    org: str,
    repo_name: str,
    token: str,
) -> bool:
    """Create GitHub repository if it doesn't exist.

    Args:
        org: GitHub organization name
        repo_name: Repository name (without org prefix)
        token: GitHub PAT token

    Returns:
        True if repo was created or already exists, False on error
    """
    import urllib.request
    import urllib.error

    # Check if repository exists
    api_url = f"https://api.github.com/repos/{org}/{repo_name}"
    req = urllib.request.Request(api_url)
    req.add_header("Authorization", f"token {token}")
    req.add_header("Accept", "application/vnd.github.v3+json")

    try:
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                print(f"  Repository {org}/{repo_name} already exists")
                return True
    except urllib.error.HTTPError as e:
        if e.code != 404:
            print(f"  ERROR: Failed to check repository: {e}")
            return False
        # 404 means repo doesn't exist, continue to create

    # Create repository
    print(f"  Creating repository {org}/{repo_name}...")
    create_url = f"https://api.github.com/orgs/{org}/repos"
    data = json.dumps(
        {
            "name": repo_name,
            "private": False,
            "auto_init": False,
        }
    ).encode("utf-8")

    req = urllib.request.Request(create_url, data=data, method="POST")
    req.add_header("Authorization", f"token {token}")
    req.add_header("Accept", "application/vnd.github.v3+json")
    req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req) as response:
            if response.status == 201:
                print(f"  ✓ Repository {org}/{repo_name} created")
                return True
            else:
                print(f"  ERROR: Unexpected status code: {response.status}")
                return False
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        print(f"  ERROR: Failed to create repository: {e}")
        print(f"  Response: {error_body}")
        return False


def push_skeleton_to_github(
    skeleton_dir: Path,
    org: str,
    repo_name: str,
    token: str,
    project_name: str,
) -> dict[str, Any]:
    """Push skeleton content to GitHub repository.

    Args:
        skeleton_dir: Directory containing skeleton structure
        org: GitHub organization name
        repo_name: Repository name (without org prefix)
        token: GitHub PAT token
        project_name: Project name for commit message

    Returns:
        Dictionary with push statistics
    """
    stats: dict[str, Any] = {
        "success": False,
        "repository": f"{org}/{repo_name}",
        "files_pushed": 0,
        "error": None,
    }

    if not skeleton_dir.exists():
        stats["error"] = f"Skeleton directory not found: {skeleton_dir}"
        return stats

    # Create repository if needed
    if not create_repo_if_needed(org, repo_name, token):
        stats["error"] = f"Failed to create repository {org}/{repo_name}"
        return stats

    # Create temporary directory for git operations
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = Path(tmpdir)
        repo_url = f"https://x-access-token:{token}@github.com/{org}/{repo_name}.git"  # noqa: E501

        print(f"  Cloning {org}/{repo_name}...")
        exit_code, stdout, stderr = run_command(
            ["git", "clone", repo_url, str(temp_path)]
        )

        # If clone fails, initialize new repo
        if exit_code != 0:
            print("  Repository empty, initializing...")
            run_command(["git", "init"], cwd=temp_path)
            run_command(["git", "remote", "add", "origin", repo_url], cwd=temp_path)

        # Copy skeleton content to temp directory
        print("  Copying skeleton content...")
        import shutil

        for item in skeleton_dir.rglob("*"):
            if item.is_file() and ".git" not in item.parts:
                rel_path = item.relative_to(skeleton_dir)
                target = temp_path / rel_path
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, target)
                stats["files_pushed"] += 1

        # Git operations
        timestamp = datetime.utcnow().strftime("%Y-%m-%d-%H:%M")
        commit_msg = f"Chore: Generated {project_name} skeleton content [{timestamp}]"  # noqa: E501

        print("  Committing changes...")
        run_command(["git", "add", "-A"], cwd=temp_path)

        # Check if there are changes to commit
        exit_code, stdout, stderr = run_command(
            ["git", "status", "--porcelain"], cwd=temp_path
        )
        if not stdout.strip():
            print("  No changes to commit")
            stats["success"] = True
            return stats

        run_command(["git", "commit", "-m", commit_msg], cwd=temp_path)

        print("  Pushing to GitHub...")
        exit_code, stdout, stderr = run_command(
            ["git", "push", "-u", "origin", "main"], cwd=temp_path
        )

        if exit_code != 0:
            # Try master branch if main fails
            exit_code, stdout, stderr = run_command(
                ["git", "push", "-u", "origin", "master"], cwd=temp_path
            )

        if exit_code != 0:
            stats["error"] = f"Failed to push: {stderr}"
            return stats

        stats["success"] = True
        print(f"  ✓ Pushed {stats['files_pushed']} files to GitHub")

    return stats


def push_overlay_to_repos(
    target_dir: Path,
    org: str,
    token: str,
    project_name: str,
) -> dict[str, Any]:
    """Push overlay content to individual repositories.

    Args:
        target_dir: Directory containing repositories with overlays
        org: GitHub organization name
        token: GitHub PAT token
        project_name: Project name for commit message

    Returns:
        Dictionary with push statistics
    """
    stats: dict[str, Any] = {
        "repos_updated": 0,
        "repos_failed": 0,
        "repositories": [],
    }

    if not target_dir.exists():
        print(f"ERROR: Target directory not found: {target_dir}")
        return stats

    # Find all git repositories in target directory
    for git_dir in target_dir.rglob(".git"):
        if not git_dir.is_dir():
            continue

        repo_path = git_dir.parent
        repo_name = repo_path.name
        repo_url = f"https://x-access-token:{token}@github.com/{org}/{repo_name}.git"  # noqa: E501

        print(f"  Processing repository: {repo_name}")

        repo_stats: dict[str, Any] = {
            "name": repo_name,
            "success": False,
            "error": None,
        }

        try:
            # Configure remote with token
            exit_code, stdout, stderr = run_command(
                ["git", "remote", "get-url", "origin"], cwd=repo_path
            )

            if exit_code == 0:
                # Update remote URL with token
                run_command(
                    ["git", "remote", "set-url", "origin", repo_url], cwd=repo_path
                )
            else:
                # Add remote if it doesn't exist
                run_command(["git", "remote", "add", "origin", repo_url], cwd=repo_path)

            # Check for changes
            exit_code, stdout, stderr = run_command(
                ["git", "status", "--porcelain"], cwd=repo_path
            )

            if not stdout.strip():
                print(f"    No changes to commit for {repo_name}")
                repo_stats["success"] = True
                stats["repositories"].append(repo_stats)
                continue

            # Commit and push changes
            timestamp = datetime.utcnow().strftime("%Y-%m-%d-%H:%M")
            commit_msg = f"CI: Deployed {project_name} workflow overlays [{timestamp}]"  # noqa: E501

            run_command(["git", "add", "-A"], cwd=repo_path)
            exit_code, stdout, stderr = run_command(
                ["git", "commit", "-m", commit_msg], cwd=repo_path
            )

            if exit_code != 0:
                repo_stats["error"] = f"Failed to commit: {stderr}"
                stats["repos_failed"] += 1
                stats["repositories"].append(repo_stats)
                continue

            exit_code, stdout, stderr = run_command(
                ["git", "push", "origin", "main"], cwd=repo_path
            )

            if exit_code != 0:
                # Try master if main fails
                exit_code, stdout, stderr = run_command(
                    ["git", "push", "origin", "master"], cwd=repo_path
                )

            if exit_code != 0:
                repo_stats["error"] = f"Failed to push: {stderr}"
                stats["repos_failed"] += 1
                stats["repositories"].append(repo_stats)
                continue

            repo_stats["success"] = True
            stats["repos_updated"] += 1
            print(f"    ✓ Pushed changes for {repo_name}")

        except Exception as e:
            repo_stats["error"] = str(e)
            stats["repos_failed"] += 1

        stats["repositories"].append(repo_stats)

    return stats


def main() -> int:
    """Push skeleton and overlay content to GitHub."""
    parser = argparse.ArgumentParser(description="Push content to GitHub repositories")
    parser.add_argument(
        "--mode",
        choices=["skeleton", "overlay"],
        required=True,
        help="Push mode: skeleton or overlay",
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        required=True,
        help="Source directory (skeleton or target with overlays)",
    )
    parser.add_argument(
        "--org",
        type=str,
        required=True,
        help="GitHub organization name",
    )
    parser.add_argument(
        "--repo",
        type=str,
        help="Repository name (for skeleton mode)",
    )
    parser.add_argument(
        "--token",
        type=str,
        required=True,
        help="GitHub PAT token",
    )
    parser.add_argument(
        "--project-name",
        type=str,
        required=True,
        help="Project name for commit messages",
    )
    parser.add_argument(
        "--stats-file",
        type=Path,
        help="Output file for push statistics (JSON)",
    )

    args = parser.parse_args()

    # Setup git configuration
    setup_git_config()

    print(f"Push mode: {args.mode}")
    print(f"Source directory: {args.source_dir}")
    print(f"Organization: {args.org}")
    print()

    try:
        if args.mode == "skeleton":
            if not args.repo:
                print("ERROR: --repo required for skeleton mode")
                return 1

            stats = push_skeleton_to_github(
                skeleton_dir=args.source_dir,
                org=args.org,
                repo_name=args.repo,
                token=args.token,
                project_name=args.project_name,
            )

            print()
            print("=" * 60)
            print("Skeleton Push Statistics:")
            print(f"  Repository: {stats['repository']}")
            print(f"  Success: {stats['success']}")
            print(f"  Files pushed: {stats['files_pushed']}")
            if stats["error"]:
                print(f"  Error: {stats['error']}")
            print("=" * 60)

            if args.stats_file:
                args.stats_file.parent.mkdir(parents=True, exist_ok=True)
                args.stats_file.write_text(json.dumps(stats, indent=2))
                print(f"\nStatistics written to: {args.stats_file}")

            return 0 if stats["success"] else 1

        elif args.mode == "overlay":
            stats = push_overlay_to_repos(
                target_dir=args.source_dir,
                org=args.org,
                token=args.token,
                project_name=args.project_name,
            )

            print()
            print("=" * 60)
            print("Overlay Push Statistics:")
            print(f"  Repositories updated: {stats['repos_updated']}")
            print(f"  Repositories failed: {stats['repos_failed']}")
            print("=" * 60)

            if args.stats_file:
                args.stats_file.parent.mkdir(parents=True, exist_ok=True)
                args.stats_file.write_text(json.dumps(stats, indent=2))
                print(f"\nStatistics written to: {args.stats_file}")

            return 0 if stats["repos_failed"] == 0 else 1

        # Should not reach here - all modes should return above
        print("ERROR: Invalid mode specified", file=sys.stderr)
        return 1

    except Exception as e:
        print(f"ERROR: Unexpected error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
