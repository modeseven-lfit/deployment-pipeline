<!--
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation
-->

# 🔨 Deployment Pipeline

This repository contains a GitHub Actions workflow that automates the
deployment of GitHub Actions workflows and content from Gerrit servers
to GitHub organizations.

## Overview

The deployment pipeline performs the following operations:

1. **Mirror Gerrit Content**: Uses the `gerrit-clone` CLI to mirror
   repositories from Gerrit servers to target GitHub organizations
2. **Extract Skeleton**: Creates a skeleton repository containing the
   `.github` directory structure from all mirrored repositories
3. **Apply Overlays**: Applies workflow overlays from a
   workflow-deployment repository to individual project repositories
4. **Push to GitHub**: Pushes both the skeleton and overlay content to
   the target GitHub organization

## Configuration

The pipeline requires two configuration sources:

### 1. PAT_TOKENS_JSON (Secret)

GitHub fine-grained PAT tokens with write permissions to target
organizations. Store this as a GitHub repository secret.

```json
[
  {
    "github_org": "modeseven-onap",
    "github_token": "github_pat_XXXX"
  },
  {
    "github_org": "modeseven-o-ran-sc",
    "github_token": "github_pat_XXXX"
  }
]
```

### 2. DEPLOY_CONFIG_JSON (Variable)

Deployment configuration defining projects, servers, and targets.
Store this as a GitHub repository variable.

```json
[
  {
    "github_username": "ModeSevenIndustrialSolutions",
    "projects": [
      {
        "project": "ONAP",
        "slug": "onap",
        "server": "gerrit.onap.org",
        "github_org": "modeseven-onap",
        "projects": "ccsdk, oom, cps",
        "deploy_repo": "modeseven-lfit/workflow-deployment",
        "skeleton_repo": "modeseven-onap/deployed-workflows",
        "prune": "true"
      }
    ]
  }
]
```

#### Configuration Fields

- `github_username`: GitHub username associated with the projects
- `project`: Full project name
- `slug`: Short project identifier (used for directory matching)
- `server`: Gerrit server hostname
- `github_org`: Target GitHub organization
- `projects`: Comma-separated list of Gerrit projects to mirror
- `deploy_repo`: Repository containing workflow overlays
- `skeleton_repo`: Repository to store the skeleton structure
- `prune`: Remove repositories without `.github` content (default:
  `true`)

## Workflow Execution

The workflow runs on manual trigger (`workflow_dispatch`) and consists
of three jobs:

### 1. check-config

Parses and checks the JSON configuration and generates a matrix for
deployment jobs.

### 2. deploy-projects

Matrix job that runs once per project configuration. Each job:

- Mirrors Gerrit repositories to GitHub
- Extracts `.github` content to create skeleton
- Clones workflow-deployment repository (if available)
- Applies workflow overlays to mirrored repositories
- Pushes skeleton to the skeleton repository
- Pushes overlays to individual project repositories

### 3. summary

Generates a deployment summary with status from all projects.

## Workflow-Deployment Structure

The workflow-deployment repository should follow this structure:

```text
workflow-deployment/
├── {slug}/
│   └── {repository-name}/
│       └── {files-and-directories}
```

Example:

```text
workflow-deployment/
├── onap/
│   └── ccsdk-features/
│       └── .github/
│           └── workflows/
│               └── test.txt
```

Files in this structure overlay the corresponding repositories in the
target GitHub organization. The repository name matching is
case-insensitive.

## Scripts

The pipeline uses Python scripts in the `scripts/` directory:

### validate_config.py

Validates JSON schemas for PAT tokens and deployment configuration.
Ensures all required fields are present and formatted properly.

### extract_github_skeleton.py

Extracts `.github` directories from cloned repositories to create a
skeleton structure. Optionally prunes repositories without workflow
content.

### apply_workflow_overlay.py

Applies workflow overlays from the workflow-deployment repository to
target repositories. Overwrites existing files.

### push_to_github.py

Pushes content to GitHub repositories. Supports two modes:

- `skeleton`: Pushes skeleton structure to a single repository
- `overlay`: Pushes overlays to project repositories

## Commit Messages

The pipeline uses standardized commit messages:

- Skeleton pushes: `Chore: Generated {PROJECT} skeleton content
  [YYYY-MM-DD-HH:MM]`
- Overlay pushes: `CI: Deployed {PROJECT} workflow overlays
  [YYYY-MM-DD-HH:MM]`

## Error Handling

- Configuration validation errors stop the workflow
- Individual project failures do not stop other projects (`fail-fast:
  false`)
- Missing workflow-deployment repository is not considered a failure
- Failed repository pushes get logged but do not stop the entire job

## Usage Example

1. Configure `PAT_TOKENS_JSON` secret with GitHub PAT tokens
2. Configure `DEPLOY_CONFIG_JSON` variable with project definitions
3. Navigate to Actions → Deployment Pipeline 🔨
4. Click "Run workflow"
5. Review job summaries and deployment statistics

## Requirements

- GitHub Actions runner with Python 3.12
- `gerrit-clone` CLI (installed automatically via `uv`)
- GitHub PAT tokens with repository write permissions

## Notes

- Archived/read-access Gerrit projects get skipped
- The skeleton repository gets created if it does not exist
- All pushed repositories are public by default
- Workflow overlays overwrite existing files with the same name
