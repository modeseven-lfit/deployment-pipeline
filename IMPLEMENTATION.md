<!--
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation
-->

# Implementation Details

This document describes the technical implementation of the deployment
pipeline, including architecture, workflow design, and script
functionality.

## Architecture Overview

The deployment pipeline consists of four main components:

1. **Configuration Management**: JSON schema validation and
   configuration parsing
2. **Gerrit Mirroring**: Using `gerrit-clone` CLI to mirror
   repositories from Gerrit to GitHub
3. **Content Processing**: Extracting `.github` content and applying
   overlays
4. **GitHub Integration**: Creating repositories and pushing content

### Data Flow

```text
[Gerrit Servers] → [gerrit-clone] → [Local Mirror]
                                          ↓
                                    [Extract .github]
                                          ↓
                                    [Skeleton Repo]
                                          ↓
[workflow-deployment] → [Apply Overlays] → [Target Repos]
                                          ↓
                                    [Push to GitHub]
```

## Workflow Architecture

### Job Structure

The workflow consists of three jobs that run sequentially with
conditional dependencies:

```yaml
check-config → deploy-projects (matrix) → summary
```

#### 1. check-config

**Purpose**: Check configuration and generate matrix for parallel
project deployments.

**Key Steps**:

- Check JSON schemas for PAT tokens and deployment configuration
- Cross-check that all configured organizations have PAT tokens
- Generate matrix configuration for parallel job execution
- Upload validated configuration as artifact

**Outputs**:

- `config-matrix`: JSON matrix for deploy-projects job
- `validated-config` artifact: Contains checked configuration files

#### 2. deploy-projects

**Purpose**: Deploy individual projects using matrix strategy.

**Matrix Strategy**: One job per project defined in configuration,
allowing parallel deployment of projects with `fail-fast:
false` to continue even if individual projects fail.

**Key Steps**:

1. Extract GitHub PAT token for target organization
2. Install `gerrit-clone` CLI via `uv` package manager
3. Mirror Gerrit repositories to GitHub using `gerrit-clone mirror`
4. Extract `.github` content to create skeleton structure
5. Clone workflow-deployment repository (if configured)
6. Apply workflow overlays to mirrored repositories
7. Push skeleton to dedicated skeleton repository
8. Push overlays to individual project repositories
9. Generate job summary with deployment statistics

**Environment**:

- Runner: `ubuntu-latest`
- Python: 3.12
- Timeout: 120 minutes
- Permissions: `contents: read`

#### 3. summary

**Purpose**: Generate deployment summary.

**Behavior**: Always runs (`if: always()`) to provide summary even
when deployments fail.

## Script Implementation

### validate_config.py

**Location**: `scripts/validate_config.py`

**Purpose**: Validates JSON configuration against defined schemas.

**Input Sources**:

- `PAT_TOKENS_JSON`: Environment variable (GitHub secret)
- `DEPLOY_CONFIG_JSON`: Environment variable (GitHub variable)
- `GITHUB_OUTPUT_DIR`: Output directory path

**Validation Rules**:

PAT Tokens:

- Must be a JSON array
- Each item must have `github_org` and `github_token` fields
- Fields must be non-empty strings

Deployment Configuration:

- Must be a JSON array
- Each user must have `github_username` and `projects` fields
- Each project must have all required fields:
  - `project`, `slug`, `server`, `github_org`
  - `projects`, `deploy_repo`, `skeleton_repo`
- Optional `prune` field defaults to `"true"`
- All organizations must have corresponding PAT tokens

**Output Files**:

- `validated_tokens.json`: Validated and normalized PAT tokens
- `validated_config.json`: Validated and normalized configuration with
  boolean conversion for `prune` field

**Exit Codes**:

- `0`: Validation successful
- `1`: Validation failed or configuration error

### extract_github_skeleton.py

**Location**: `scripts/extract_github_skeleton.py`

**Purpose**: Extract `.github` directories from cloned repositories to
create skeleton structure.

**Algorithm**:

1. Recursively search source directory for `.git` directories
2. For each git repository found:
   - Check for `.github` directory
   - If present, copy entire `.github` tree to output directory
   - Preserve directory hierarchy relative to source root
   - If pruning enabled, skip repositories without `.github` content
3. Generate statistics on extracted content

**Arguments**:

- `--source-dir`: Root directory containing cloned repositories
- `--output-dir`: Destination for skeleton structure
- `--prune-empty`: Remove repositories without `.github` (default)
- `--no-prune-empty`: Keep all repository directories
- `--stats-file`: Optional JSON output for statistics

**Statistics**:

- Total repositories processed
- Repositories with `.github` content
- Repositories without `.github` content
- Total files copied
- Per-repository details

**File Operations**:

- Uses `shutil.copy2()` to preserve file metadata
- Creates parent directories as needed
- Maintains relative path structure with hierarchy intact

### apply_workflow_overlay.py

**Location**: `scripts/apply_workflow_overlay.py`

**Purpose**: Apply workflow overlays from workflow-deployment
repository to target repositories.

**Overlay Structure**:

```text
overlay-dir/
└── {project-slug}/
    └── {repository-name}/
        └── {files-and-directories}
```

**Algorithm**:

1. Locate project slug directory in overlay root
2. For each repository directory under project slug:
   - Search target directory for matching repository (case-insensitive)
   - Copy all files from overlay to target repository
   - Overwrite existing files with same name
   - Track statistics on files copied and overwritten
3. Generate overlay statistics

**Arguments**:

- `--overlay-dir`: Workflow-deployment repository root
- `--target-dir`: Directory containing target repositories
- `--project-slug`: Project slug to match in overlay
- `--stats-file`: Optional JSON output for statistics

**Matching Rules**:

- Repository name matching is case-insensitive
- Script preserves full directory hierarchy during copy
- Missing target repositories generate warnings but do not fail

**Statistics**:

- Repositories updated
- Total files copied
- Files overwritten
- Per-repository details with status

### push_to_github.py

**Location**: `scripts/push_to_github.py`

**Purpose**: Push content to GitHub repositories with automatic
repository creation.

**Operating Modes**:

#### Skeleton Mode

- Pushes entire directory structure to single repository
- Creates repository if it doesn't exist
- Commits with message: `Chore: Generated {PROJECT} skeleton content
  [timestamp]`

#### Overlay Mode

- Pushes changes to project repositories
- Commits repositories with changes
- Commits with message: `CI: Deployed {PROJECT} workflow overlays
  [timestamp]`

**Arguments**:

- `--mode`: Operation mode (`skeleton` or `overlay`)
- `--source-dir`: Source directory to push
- `--org`: GitHub organization name
- `--repo`: Repository name (required for skeleton mode)
- `--token`: GitHub PAT token
- `--project-name`: Project name for commit messages
- `--stats-file`: Optional JSON output for statistics

**GitHub API Integration**:

Repository Creation:

1. Check if repository exists using GET `/repos/{org}/{repo}`
2. If not found (404), create using POST `/orgs/{org}/repos`
3. Repository created as public with no initialization

Authentication:

- Uses PAT token in Authorization header for API calls
- Uses token in remote URL for git operations:
  `https://x-access-token:{token}@github.com/{org}/{repo}.git`

**Git Operations**:

Skeleton Push:

1. Clone existing repository or initialize new
2. Copy all files from source directory
3. Add all files: `git add -A`
4. Check for changes: `git status --porcelain`
5. Commit if changes exist
6. Push to `main` branch (fallback to `master` if main fails)

Overlay Push:

1. For each repository with `.git` directory:
2. Configure remote URL with token
3. Check for uncommitted changes
4. Commit and push repositories with changes
5. Try `main` branch first, fallback to `master`

**Error Handling**:

- API errors include response body for debugging
- Scripts capture and report git operation failures
- Per-repository errors don't stop processing of other repositories
- Statistics output collects all errors

## Security Considerations

### Token Handling

**Storage**:

- PAT tokens stored in GitHub Secrets (encrypted at rest)
- Never logged or exposed in workflow output
- Passed via environment variables to scripts

**Usage**:

- Tokens used in memory, never written to disk
- Git operations use token in HTTPS URL (ephemeral)
- Temporary directories cleaned up after use

**Permissions**:

- Fine-grained tokens recommended over classic PATs
- Required permissions:
  - Repository: Contents (Read and write)
  - Repository: Metadata (Read access)
  - Repository: Administration (Read and write for creation)

### Workflow Security

**Runner Hardening**:

- Uses `step-security/harden-runner` action
- Egress policy set to audit mode
- All external dependencies pinned by SHA

**Permission Scoping**:

- Workflow uses minimal permissions (`contents: read`)
- No write access to workflow repository
- Token permissions scoped per organization

## Performance Considerations

### Parallel Execution

**Matrix Strategy**:

- Projects deploy in parallel (one job per project)
- Parallelism limited by GitHub runner availability
- `fail-fast: false` allows independent project execution

**Resource Usage**:

- Each job runs in isolated runner environment
- Timeout set to 120 minutes per project
- Temporary files stored in `${{ runner.temp }}`

### Optimization Opportunities

**Caching**:

- Could cache `gerrit-clone` CLI installation
- Could cache Python dependencies (none exist)
- Could reuse mirrored content across runs

**Incremental Updates**:

- Performs full mirror on each run
- Could add change detection to skip unchanged repositories
- Could use git operations to push changed files

## Error Handling Strategy

### Validation Phase

- Strict validation with immediate failure
- Clear error messages for configuration issues
- Prevents execution with invalid configuration

### Deployment Phase

- Individual project failures don't stop other projects
- Per-repository errors captured and reported
- Continue-on-error for optional operations (workflow-deployment)

### Reporting

- Job summaries show per-project status
- Statistics artifacts available for debugging
- Comprehensive logging at each step

## Extension Points

### Adding New Processing Steps

Add steps to the deploy-projects job to extend the pipeline:

```yaml
- name: "Custom Processing"
  run: |
    python scripts/custom_script.py \
      --input "${{ runner.temp }}/mirror-${{ matrix.slug }}" \
      --output "${{ runner.temp }}/processed"
```

### Custom Validation Rules

Extend `validate_config.py` with custom checks:

```python
def validate_custom_field(project: dict) -> None:
    """Add custom validation logic."""
    if "custom_field" in project:
        # Check custom field
        pass
```

### Output Formats

Scripts support JSON statistics output for integration with other
tools:

```bash
python scripts/extract_github_skeleton.py \
  --stats-file /tmp/stats.json
```

## Testing

### Unit Testing

Test individual scripts in isolation:

```bash
# Test configuration validation
export PAT_TOKENS_JSON='[...]'
export DEPLOY_CONFIG_JSON='[...]'
python scripts/validate_config.py

# Test skeleton extraction
python scripts/extract_github_skeleton.py \
  --source-dir /path/to/test/data \
  --output-dir /tmp/output
```

### Integration Testing

Full workflow testing requires:

1. Test GitHub organizations
2. Test PAT tokens with limited permissions
3. Test Gerrit server access or mock data

### Workflow Validation

Use `actionlint` to check workflow syntax:

```bash
actionlint .github/workflows/deploy.yaml
```

Use `yamllint` to check YAML formatting:

```bash
yamllint .github/workflows/deploy.yaml
```

## Maintenance

### Updating Dependencies

**gerrit-clone CLI**:

- Installed via `uv` (automatically gets latest version)
- Pin to specific version if stability required

**GitHub Actions**:

- All actions pinned by SHA for security
- Update SHAs when new versions available
- Test updates in separate branch before merging

### Monitoring

**Workflow Runs**:

- Review job summaries for deployment status
- Review artifact uploads for statistics
- Check logs for warnings and errors

**Repository Health**:

- Verify skeleton repository stays current
- Check individual repositories for overlay application
- Watch for API rate limits or token expiry

## Troubleshooting

### Common Issues

**Configuration Validation Failure**:

- Check JSON syntax with validator
- Verify all required fields present
- Ensure PAT tokens exist for all organizations

**Mirror Operation Timeout**:

- Increase timeout in workflow (default: 120 minutes)
- Reduce number of projects in filter
- Check Gerrit server connectivity

**Push Permission Denied**:

- Verify PAT token permissions
- Check token expiry
- Ensure organization access granted

### Debug Mode

Enable verbose output in scripts:

```bash
# Most scripts support detailed output by default
python scripts/extract_github_skeleton.py --verbose
```

Enable verbose git operations:

```bash
export GIT_TRACE=1
export GIT_CURL_VERBOSE=1
```

## Future Enhancements

Potential improvements for future versions:

1. **Incremental Mirroring**: Process changed repositories
2. **Parallel Repository Processing**: Speed up push operations
3. **Dry Run Mode**: Preview changes without pushing
4. **Webhook Triggers**: Automatic deployment on Gerrit changes
5. **Notification Integration**: Slack/email notifications
6. **Metrics Dashboard**: Visualize deployment statistics
7. **Rollback Capability**: Revert to previous deployment state
8. **Multi-Branch Support**: Deploy different branches separately
