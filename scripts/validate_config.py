#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""Validate deployment configuration and PAT tokens JSON schemas."""

import json
import sys
from pathlib import Path
from typing import Any


def validate_pat_tokens(data: Any) -> list[dict[str, str]]:
    """Validate PAT_TOKENS_JSON structure.

    Expected structure:
    [
      {"github_org": "org-name", "github_token": "token"},
      ...
    ]
    """
    if not isinstance(data, list):
        raise ValueError("PAT_TOKENS_JSON must be a JSON array")

    if not data:
        raise ValueError("PAT_TOKENS_JSON cannot be empty")

    validated_tokens = []
    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"PAT_TOKENS_JSON[{idx}] must be an object")

        if "github_org" not in item:
            raise ValueError(f"PAT_TOKENS_JSON[{idx}] missing 'github_org'")
        if "github_token" not in item:
            raise ValueError(f"PAT_TOKENS_JSON[{idx}] missing 'github_token'")

        if not isinstance(item["github_org"], str):
            raise ValueError(f"PAT_TOKENS_JSON[{idx}].github_org must be a string")
        if not isinstance(item["github_token"], str):
            raise ValueError(f"PAT_TOKENS_JSON[{idx}].github_token must be a string")

        if not item["github_org"].strip():
            raise ValueError(f"PAT_TOKENS_JSON[{idx}].github_org cannot be empty")
        if not item["github_token"].strip():
            raise ValueError(f"PAT_TOKENS_JSON[{idx}].github_token cannot be empty")

        validated_tokens.append(
            {
                "github_org": item["github_org"].strip(),
                "github_token": item["github_token"].strip(),
            }
        )

    return validated_tokens


def validate_deploy_config(data: Any) -> list[dict[str, Any]]:
    """Validate DEPLOY_CONFIG_JSON structure.

    Expected structure:
    [
      {
        "github_username": "username",
        "projects": [
          {
            "project": "Project Name",
            "slug": "slug",
            "server": "gerrit.example.org",
            "github_org": "org-name",
            "projects": "proj1, proj2",
            "deploy_repo": "owner/repo",
            "skeleton_repo": "owner/repo",
            "prune": "true"  # optional, defaults to "true"
          },
          ...
        ]
      },
      ...
    ]
    """
    if not isinstance(data, list):
        raise ValueError("DEPLOY_CONFIG_JSON must be a JSON array")

    if not data:
        raise ValueError("DEPLOY_CONFIG_JSON cannot be empty")

    validated_users = []
    for user_idx, user_item in enumerate(data):
        if not isinstance(user_item, dict):
            raise ValueError(f"DEPLOY_CONFIG_JSON[{user_idx}] must be an object")

        if "github_username" not in user_item:
            raise ValueError(
                f"DEPLOY_CONFIG_JSON[{user_idx}] missing 'github_username'"
            )
        if "projects" not in user_item:
            raise ValueError(f"DEPLOY_CONFIG_JSON[{user_idx}] missing 'projects'")

        username = user_item["github_username"]
        if not isinstance(username, str):
            raise ValueError(
                f"DEPLOY_CONFIG_JSON[{user_idx}].github_username must be a string"
            )
        if not username.strip():
            raise ValueError(
                f"DEPLOY_CONFIG_JSON[{user_idx}].github_username cannot be empty"
            )

        projects = user_item["projects"]
        if not isinstance(projects, list):
            raise ValueError(
                f"DEPLOY_CONFIG_JSON[{user_idx}].projects must be an array"
            )
        if not projects:
            raise ValueError(f"DEPLOY_CONFIG_JSON[{user_idx}].projects cannot be empty")

        validated_projects = []
        for proj_idx, proj in enumerate(projects):
            if not isinstance(proj, dict):
                raise ValueError(
                    f"DEPLOY_CONFIG_JSON[{user_idx}].projects[{proj_idx}] "
                    "must be an object"
                )

            required_fields = [
                "project",
                "slug",
                "server",
                "github_org",
                "projects",
                "deploy_repo",
                "skeleton_repo",
            ]

            for field in required_fields:
                if field not in proj:
                    raise ValueError(
                        f"DEPLOY_CONFIG_JSON[{user_idx}]."
                        f"projects[{proj_idx}] missing '{field}'"
                    )
                if not isinstance(proj[field], str):
                    raise ValueError(
                        f"DEPLOY_CONFIG_JSON[{user_idx}]."
                        f"projects[{proj_idx}].{field} "
                        "must be a string"
                    )
                if not proj[field].strip():
                    raise ValueError(
                        f"DEPLOY_CONFIG_JSON[{user_idx}]."
                        f"projects[{proj_idx}].{field} "
                        "cannot be empty"
                    )

            # Validate prune field (optional, defaults to "true")
            prune = proj.get("prune", "true")
            if not isinstance(prune, str):
                raise ValueError(
                    f"DEPLOY_CONFIG_JSON[{user_idx}]."
                    f"projects[{proj_idx}].prune must be a string"
                )
            prune_lower = prune.strip().lower()
            if prune_lower not in ("true", "false"):
                raise ValueError(
                    f"DEPLOY_CONFIG_JSON[{user_idx}]."
                    f"projects[{proj_idx}].prune must be "
                    "'true' or 'false'"
                )

            validated_projects.append(
                {
                    "project": proj["project"].strip(),
                    "slug": proj["slug"].strip(),
                    "server": proj["server"].strip(),
                    "github_org": proj["github_org"].strip(),
                    "projects": proj["projects"].strip(),
                    "deploy_repo": proj["deploy_repo"].strip(),
                    "skeleton_repo": proj["skeleton_repo"].strip(),
                    "prune": prune_lower == "true",
                }
            )

        validated_users.append(
            {
                "github_username": username.strip(),
                "projects": validated_projects,
            }
        )

    return validated_users


def main() -> int:
    """Validate configuration from environment or files."""
    import os

    # Read PAT tokens
    pat_tokens_json = os.environ.get("PAT_TOKENS_JSON", "")
    if not pat_tokens_json:
        print("ERROR: PAT_TOKENS_JSON environment variable not set")
        return 1

    # Read deploy config
    deploy_config_json = os.environ.get("DEPLOY_CONFIG_JSON", "")
    if not deploy_config_json:
        print("ERROR: DEPLOY_CONFIG_JSON environment variable not set")
        return 1

    try:
        # Parse PAT tokens
        pat_data = json.loads(pat_tokens_json)
        validated_tokens = validate_pat_tokens(pat_data)
        print(f"✓ PAT_TOKENS_JSON valid ({len(validated_tokens)} orgs)")

        # Parse deploy config
        config_data = json.loads(deploy_config_json)
        validated_config = validate_deploy_config(config_data)
        print(f"✓ DEPLOY_CONFIG_JSON valid ({len(validated_config)} users)")

        # Count total projects
        total_projects = sum(len(user["projects"]) for user in validated_config)
        print(f"✓ Total projects to deploy: {total_projects}")

        # Verify all github_orgs have corresponding PAT tokens
        token_orgs = {t["github_org"] for t in validated_tokens}
        config_orgs = set()
        for user in validated_config:
            for project in user["projects"]:
                config_orgs.add(project["github_org"])

        missing_tokens = config_orgs - token_orgs
        if missing_tokens:
            print(
                f"ERROR: Missing PAT tokens for orgs: "
                f"{', '.join(sorted(missing_tokens))}"
            )
            return 1

        print("✓ All organizations have PAT tokens configured")

        # Output validated configuration to files
        output_dir = Path(os.environ.get("GITHUB_OUTPUT_DIR", "/tmp"))
        output_dir.mkdir(parents=True, exist_ok=True)

        tokens_file = output_dir / "validated_tokens.json"
        config_file = output_dir / "validated_config.json"

        tokens_file.write_text(json.dumps(validated_tokens, indent=2))
        config_file.write_text(json.dumps(validated_config, indent=2))

        print(f"✓ Validated tokens written to: {tokens_file}")
        print(f"✓ Validated config written to: {config_file}")

        return 0

    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON: {e}")
        return 1
    except ValueError as e:
        print(f"ERROR: Validation failed: {e}")
        return 1
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
