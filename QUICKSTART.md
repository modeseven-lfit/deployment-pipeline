<!--
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation
-->

# Quick Start Guide

Get the deployment pipeline running in under 10 minutes.

## Prerequisites

- Admin access to target GitHub organizations
- Access to Gerrit servers you want to mirror

## Step 1: Create GitHub PAT Tokens (5 minutes)

For each target GitHub organization:

1. Go to GitHub Settings → Developer settings → Personal access
   tokens → Fine-grained tokens
2. Click "Generate new token"
3. Configure:
   - **Name**: `Deployment Pipeline - {ORG_NAME}`
   - **Valid for**: 90 days (or as needed)
   - **Repository access**: All repositories
   - **Permissions**:
     - Contents: Read and write
     - Metadata: Read access
     - Administration: Read and write
4. Generate and copy the token

## Step 2: Configure Secrets and Variables (3 minutes)

### Add PAT Tokens Secret

1. Navigate to deployment-pipeline repository
2. Settings → Secrets and variables → Actions
3. Click "New repository secret"
4. Name: `PAT_TOKENS_JSON`
5. Value:

```json
[
  {
    "github_org": "your-org-name",
    "github_token": "github_pat_YOUR_TOKEN_HERE"
  }
]
```

### Add Deployment Configuration Variable

1. Click the "Variables" tab
2. Click "New repository variable"
3. Name: `DEPLOY_CONFIG_JSON`
4. Value:

```json
[
  {
    "github_username": "YourGitHubUsername",
    "projects": [
      {
        "project": "Project Name",
        "slug": "project-slug",
        "server": "gerrit.example.org",
        "github_org": "your-org-name",
        "projects": "project1, project2",
        "deploy_repo": "your-username/workflow-deployment",
        "skeleton_repo": "your-org-name/workflows-skeleton",
        "prune": "true"
      }
    ]
  }
]
```

Replace:

- `YourGitHubUsername`: Your GitHub username
- `Project Name`: Full project name
- `project-slug`: Short identifier (lowercase, no spaces)
- `gerrit.example.org`: Your Gerrit server
- `your-org-name`: Target GitHub organization
- `project1, project2`: Gerrit projects to mirror
- `your-username/workflow-deployment`: Your overlay repository
- `your-org-name/workflows-skeleton`: Skeleton repository name

## Step 3: Run the Pipeline (2 minutes)

1. Navigate to Actions → Deployment Pipeline 🔨
2. Click "Run workflow"
3. Select `main` branch
4. Click "Run workflow"

The pipeline will:

- Check configuration
- Mirror Gerrit repositories to GitHub
- Extract `.github` content
- Create skeleton repository
- Apply workflow overlays (if configured)
- Push everything to GitHub

## Verify Results

After the workflow completes:

1. Check the job summary for statistics
2. Visit your GitHub organization to see mirrored repositories
3. Check the skeleton repository for workflow content
4. Review individual repositories for applied overlays

## Next Steps

- Review [USAGE.md](USAGE.md) for detailed configuration options
- Set up a workflow-deployment repository for custom overlays
- Configure projects or organizations
- Schedule automated deployments

## Troubleshooting

### Configuration validation fails

Check that:

- JSON syntax is correct (use a JSON validator)
- All required fields are present
- PAT tokens match configured organizations

### Mirror operation fails

Verify:

- Gerrit server is accessible
- PAT tokens have correct permissions
- GitHub organization exists

### Need help?

1. Check workflow logs for detailed error messages
2. Review [USAGE.md](USAGE.md) for common issues
3. Examine example configurations in `examples/` directory

## Example for Testing

Use this minimal configuration to test the pipeline:

```json
{
  "PAT_TOKENS_JSON": [
    {
      "github_org": "test-org",
      "github_token": "github_pat_YOUR_TOKEN"
    }
  ],
  "DEPLOY_CONFIG_JSON": [
    {
      "github_username": "testuser",
      "projects": [
        {
          "project": "Test Project",
          "slug": "test",
          "server": "gerrit.example.org",
          "github_org": "test-org",
          "projects": "test-project",
          "deploy_repo": "",
          "skeleton_repo": "test-org/test-skeleton",
          "prune": "true"
        }
      ]
    }
  ]
}
```

This configuration:

- Mirrors one project from Gerrit
- Creates a skeleton repository
- Skips workflow overlays (empty `deploy_repo`)
- Ideal for initial testing
