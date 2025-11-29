<!--
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation
-->

# Configuration Examples

This directory contains example configuration files for the deployment
pipeline.

## Files

### pat_tokens.json

Example PAT tokens configuration for GitHub organizations.

**Usage**: Copy this content to the `PAT_TOKENS_JSON` GitHub secret in
your deployment-pipeline repository.

**Important**: Replace the example tokens with actual GitHub
fine-grained PAT tokens before use.

**Required Permissions**:

- Repository permissions:
  - Contents: Read and write
  - Metadata: Read access
  - Administration: Read and write (for repository creation)

### deploy_config.json

Example deployment configuration for projects.

**Usage**: Copy this content to the `DEPLOY_CONFIG_JSON` GitHub
variable in your deployment-pipeline repository.

**Customization**: Update the following fields for your setup:

- `github_username`: Your GitHub username
- `server`: Gerrit server hostname
- `github_org`: Target GitHub organization
- `projects`: Comma-separated list of Gerrit projects
- `deploy_repo`: Your workflow-deployment repository
- `skeleton_repo`: Your skeleton repository name
- `prune`: Set to `"true"` or `"false"` based on your needs

## Testing Configuration

Use the validation script to test your configuration:

```bash
export PAT_TOKENS_JSON='<paste-content-here>'
export DEPLOY_CONFIG_JSON='<paste-content-here>'
export GITHUB_OUTPUT_DIR=/tmp/config
python ../scripts/validate_config.py
```

## Security Notes

- Never commit actual PAT tokens to version control
- Use GitHub Secrets for `PAT_TOKENS_JSON`
- Use GitHub Variables for `DEPLOY_CONFIG_JSON`
- Rotate tokens on a schedule
- Use fine-grained tokens with minimal required permissions
