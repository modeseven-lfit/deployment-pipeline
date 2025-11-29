<!--
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation
-->

# Deployment Pipeline Scripts

This directory contains Python scripts used by the deployment pipeline
workflow to mirror, extract, and deploy GitHub Actions content from
Gerrit servers.

## Scripts Overview

### validate_config.py

Validates the JSON configuration for PAT tokens and deployment
settings.

**Usage:**

```bash
export PAT_TOKENS_JSON='[{"github_org": "...", "github_token": "..."}]'
export DEPLOY_CONFIG_JSON='[{"github_username": "...", "projects": [...]}]'
export GITHUB_OUTPUT_DIR=/tmp/config
python validate_config.py
```

**Outputs:**

- `validated_tokens.json`: Validated PAT token configuration
- `validated_config.json`: Validated deployment configuration
- Exit code 0 on success, 1 on validation failure

**Validation Rules:**

- All required fields must be present and non-empty
- PAT tokens must exist for all configured organizations
- Project configurations must include all required fields
- The `prune` field defaults to `"true"` if not specified

### extract_github_skeleton.py

Extracts `.github` directories from cloned repositories to create a
skeleton structure containing workflow content.

**Usage:**

```bash
python extract_github_skeleton.py \
  --source-dir /path/to/cloned/repos \
  --output-dir /path/to/skeleton \
  --prune-empty \
  --stats-file /tmp/skeleton-stats.json
```

**Arguments:**

- `--source-dir`: Directory containing cloned Gerrit repositories
- `--output-dir`: Output directory for skeleton structure
- `--prune-empty`: Remove repositories without `.github` content
- `--no-prune-empty`: Keep all repositories (creates empty
  directories)
- `--stats-file`: Optional JSON file for extraction statistics

**Statistics Output:**

```json
{
  "total_repos": 19,
  "repos_with_github": 8,
  "repos_without_github": 11,
  "total_files": 42,
  "repositories": [
    {
      "path": "ccsdk/features",
      "has_github": true,
      "files_copied": 5
    }
  ]
}
```

### apply_workflow_overlay.py

Applies workflow overlays from the workflow-deployment repository to
target repositories.

**Usage:**

```bash
python apply_workflow_overlay.py \
  --overlay-dir /path/to/workflow-deployment \
  --target-dir /path/to/cloned/repos \
  --project-slug onap \
  --stats-file /tmp/overlay-stats.json
```

**Arguments:**

- `--overlay-dir`: Directory containing workflow-deployment overlays
- `--target-dir`: Target directory with cloned repositories
- `--project-slug`: Project slug to match in overlay structure
- `--stats-file`: Optional JSON file for overlay statistics

**Overlay Structure:**

The script expects overlays in this format:

```text
overlay-dir/
└── {project-slug}/
    └── {repository-name}/
        └── {files-and-directories}
```

**Statistics Output:**

```json
{
  "overlay_dir": "/path/to/workflow-deployment",
  "target_dir": "/path/to/cloned/repos",
  "project_slug": "onap",
  "repos_updated": 3,
  "files_copied": 12,
  "files_overwritten": 4,
  "repositories": [
    {
      "name": "ccsdk-features",
      "status": "updated",
      "files_copied": 4,
      "files_overwritten": 1
    }
  ]
}
```

**Matching Rules:**

- Repository name matching is case-insensitive
- Script preserves full directory hierarchy during copy
- The script copies files recursively from the overlay structure
- Existing files are overwritten
- Missing target repositories generate warnings but do not fail

### push_to_github.py

Pushes content to GitHub repositories. Supports two modes: skeleton
and overlay.

**Usage (Skeleton Mode):**

```bash
python push_to_github.py \
  --mode skeleton \
  --source-dir /path/to/skeleton \
  --org modeseven-onap \
  --repo deployed-workflows \
  --token github_pat_XXXX \
  --project-name ONAP \
  --stats-file /tmp/push-stats.json
```

**Usage (Overlay Mode):**

```bash
python push_to_github.py \
  --mode overlay \
  --source-dir /path/to/cloned/repos \
  --org modeseven-onap \
  --token github_pat_XXXX \
  --project-name ONAP \
  --stats-file /tmp/push-stats.json
```

**Arguments:**

- `--mode`: Push mode (`skeleton` or `overlay`)
- `--source-dir`: Source directory to push
- `--org`: GitHub organization name
- `--repo`: Repository name (required for skeleton mode)
- `--token`: GitHub PAT token with write permissions
- `--project-name`: Project name for commit messages
- `--stats-file`: Optional JSON file for push statistics

**Skeleton Mode:**

- Creates the repository if it does not exist
- Pushes all content from source directory to a single repository
- Commit message: `Chore: Generated {PROJECT} skeleton content
  [YYYY-MM-DD-HH:MM]`

**Overlay Mode:**

- Pushes changes to project repositories
- Commits and pushes repositories with changes
- Commit message: `CI: Deployed {PROJECT} workflow overlays
  [YYYY-MM-DD-HH:MM]`

**Statistics Output (Skeleton):**

```json
{
  "success": true,
  "repository": "modeseven-onap/deployed-workflows",
  "files_pushed": 42,
  "error": null
}
```

**Statistics Output (Overlay):**

```json
{
  "repos_updated": 8,
  "repos_failed": 0,
  "repositories": [
    {
      "name": "ccsdk-features",
      "success": true,
      "error": null
    }
  ]
}
```

## Development

### Running Scripts Locally

Python 3.11+ must be present:

```bash
python3 --version
```

Run scripts with appropriate arguments:

```bash
cd deployment-pipeline
python scripts/validate_config.py
```

### Testing

The scripts include error handling and validation. Test with sample
data:

```bash
export PAT_TOKENS_JSON='[{"github_org":"test","github_token":"xxx"}]'
export DEPLOY_CONFIG_JSON='[{"github_username":"test","projects":[]}]'
python scripts/validate_config.py
```

## Dependencies

The scripts use Python standard library:

- `json`: JSON parsing and generation
- `pathlib`: File path handling
- `subprocess`: Git command execution
- `argparse`: Command-line argument parsing
- `tempfile`: Temporary directory creation
- `shutil`: File operations
- `urllib`: HTTP requests for GitHub API

No extra packages needed.

## Error Handling

All scripts follow these error handling conventions:

- Exit code 0 indicates success
- Exit code 1 indicates failure
- Scripts print errors to stderr
- Scripts include stack traces for unexpected errors
- Validation errors include descriptive messages

## Git Configuration

The `push_to_github.py` script automatically configures git:

```bash
git config --global user.name "GitHub Actions"
git config --global user.email "actions@github.com"
```

Git needs this configuration for commits but it does not persist outside
the GitHub Actions runner environment.
