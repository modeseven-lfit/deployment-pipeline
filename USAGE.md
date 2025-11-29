<!--
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation
-->

# Deployment Pipeline Usage Guide

This guide walks you through setting up and running the deployment
pipeline to mirror Gerrit repositories to GitHub and deploy workflow
content.

## Prerequisites

- GitHub organization(s) with admin access
- GitHub fine-grained PAT tokens with repository write permissions
- Access to Gerrit servers you want to mirror
- A workflow-deployment repository (optional, for overlays)

## Step 1: Create GitHub PAT Tokens

Create fine-grained PAT tokens for each target GitHub organization:

1. Navigate to GitHub Settings → Developer settings → Personal access
   tokens → Fine-grained tokens
2. Click "Generate new token"
3. Configure the token:
   - **Name**: Deployment Pipeline - {ORG_NAME}
   - **Valid for**: Set token validity period
   - **Repository access**: All repositories
   - **Permissions**:
     - Repository permissions:
       - Contents: Read and write
       - Metadata: Read access
       - Administration: Read and write (for repository creation)

4. Generate and save the token securely

Repeat for each target organization.

## Step 2: Configure PAT Tokens Secret

1. Navigate to your deployment-pipeline repository
2. Go to Settings → Secrets and variables → Actions
3. Click "New repository secret"
4. Name: `PAT_TOKENS_JSON`
5. Value: JSON array with your tokens

```json
[
  {
    "github_org": "modeseven-onap",
    "github_token": "github_pat_11AAAAAA..."
  },
  {
    "github_org": "modeseven-o-ran-sc",
    "github_token": "github_pat_11BBBBBB..."
  },
  {
    "github_org": "modeseven-opendaylight",
    "github_token": "github_pat_11CCCCCC..."
  }
]
```

## Step 3: Configure Deployment Settings Variable

1. In the same repository, go to Settings → Secrets and variables →
   Actions
2. Click the "Variables" tab
3. Click "New repository variable"
4. Name: `DEPLOY_CONFIG_JSON`
5. Value: JSON array with your project configurations

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
      },
      {
        "project": "OpenDaylight",
        "slug": "odl",
        "server": "git.opendaylight.org",
        "github_org": "modeseven-opendaylight",
        "projects": "yangtools, serviceutils",
        "deploy_repo": "modeseven-lfit/workflow-deployment",
        "skeleton_repo": "modeseven-opendaylight/deployed-workflows",
        "prune": "true"
      }
    ]
  }
]
```

### Configuration Fields Explained

#### Top-Level Fields

- `github_username`: GitHub username associated with the projects
  (used for organization and tracking)

#### Project Configuration Fields

- `project`: Full project name (e.g., "ONAP", "OpenDaylight")
- `slug`: Short identifier for the project, used for directory
  matching in overlays (e.g., "onap", "odl")
- `server`: Gerrit server hostname (e.g., "gerrit.onap.org")
- `github_org`: Target GitHub organization name
- `projects`: Comma-separated list of Gerrit projects to mirror.
  Parent projects will include all child projects.
- `deploy_repo`: Repository containing workflow overlays in format
  `owner/repo`
- `skeleton_repo`: Repository to store skeleton structure in format
  `owner/repo`
- `prune`: Set to `"true"` to remove repositories without `.github`
  content from skeleton, or `"false"` to keep all repositories

## Step 4: Set Up Workflow-Deployment Repository (Optional)

If you want to deploy custom workflows to specific repositories,
create a workflow-deployment repository:

1. Create a new repository (e.g., `workflow-deployment`)
2. Structure the repository as follows:

```text
workflow-deployment/
├── {slug}/
│   └── {repository-name}/
│       └── {files-and-directories}
```

Example structure:

```text
workflow-deployment/
├── onap/
│   ├── ccsdk-features/
│   │   └── .github/
│   │       └── workflows/
│   │           └── ci.yaml
│   └── oom/
│       └── .github/
│           └── workflows/
│               └── deploy.yaml
├── odl/
│   └── yangtools/
│       └── .github/
│           └── workflows/
│               └── test.yaml
```

### Overlay Behavior

- Files in the overlay repository overwrite existing files in target
  repositories
- Repository name matching is case-insensitive
- Missing target repositories generate warnings but do not fail the
  deployment

## Step 5: Run the Deployment Pipeline

1. Navigate to Actions → Deployment Pipeline 🔨
2. Click "Run workflow"
3. Select the branch (default: `main`)
4. Click "Run workflow"

The pipeline will:

1. Parse and check your JSON configuration
2. Create matrix jobs for each project
3. For each project:
   - Mirror Gerrit repositories to GitHub
   - Extract `.github` content to skeleton
   - Clone workflow-deployment repository (if configured)
   - Apply workflow overlays (if available)
   - Push skeleton to skeleton repository
   - Push overlays to individual repositories

## Deployment Monitoring

### Job Summary

Each project job generates a summary showing:

- Project details (name, slug, server, organization)
- Skeleton extraction statistics
- Workflow overlay statistics

### Artifacts

The workflow uploads deployment statistics as artifacts:

- `validated-config`: Checked configuration files
- `stats-{slug}`: Per-project deployment statistics

Download artifacts to review detailed deployment information.

### Logs

Check the workflow logs for detailed information about each step:

- Mirror operations
- File extraction and copying
- Git push operations
- Any errors or warnings

## Troubleshooting

### Configuration Validation Fails

**Error**: "PAT_TOKENS_JSON must be a JSON array"

**Solution**: Ensure your secret contains valid JSON. Use a JSON
validator to check syntax.

**Error**: "Missing PAT tokens for orgs: ..."

**Solution**: Add PAT tokens for all organizations listed in your
deployment configuration.

### Mirror Operation Fails

**Error**: "Failed to mirror repositories"

**Solution**: Verify:

- Gerrit server hostname is correct
- GitHub PAT token has correct permissions
- GitHub organization exists and token has access

### Repository Not Found in Overlay

**Warning**: "Repository 'xyz' not found in target directory"

**Solution**: This warning indicates the overlay references a
repository that was not mirrored. Verify:

- Repository name matches (case-insensitive)
- Repository exists in the mirror operation
- Repository is not archived/read-access

### Push Operation Fails

**Error**: "Failed to push: permission denied"

**Solution**: Verify PAT token has write permissions:

- Repository permissions: Contents (Read and write)
- Organization permissions: Administration (Read and write) for repo
  creation

### No Changes to Commit

**Info**: "No changes to commit"

**Solution**: This is normal behavior when:

- Skeleton content has not changed since last run
- No overlay files have changed
- The operation completed with no updates needed

## Advanced Configuration

### Filtering Gerrit Projects

Use the `projects` field to filter which Gerrit projects to mirror:

```json
"projects": "ccsdk, oom, cps"
```

This mirrors:

- The `ccsdk` project and all child projects
- The `oom` project and all child projects
- The `cps` project and all child projects

For hierarchical projects like `ccsdk/features`, specifying `ccsdk`
will include all child projects automatically.

### Disabling Pruning

To keep all repositories in the skeleton, even those without `.github`
content:

```json
"prune": "false"
```

This creates empty directories for repositories without workflow
content.

### Users

The configuration supports users with different project sets:

```json
[
  {
    "github_username": "UserOne",
    "projects": [...]
  },
  {
    "github_username": "UserTwo",
    "projects": [...]
  }
]
```

Each user's projects run in separate matrix jobs.

## Best Practices

1. **Test with Small Project Sets**: Start with a small number of
   projects to verify configuration before scaling up

2. **Use Descriptive Slugs**: Choose short, memorable slugs that
   identify projects

3. **Keep Tokens Secure**: Never commit PAT tokens to repositories.
   Always use GitHub Secrets.

4. **Review Skeleton Repository**: After the first run, review the
   skeleton repository to ensure it contains expected content

5. **Version Control Overlays**: Keep your workflow-deployment
   repository under version control to track changes

6. **Review Deployment Logs**: Check logs for warnings and errors,
   even when deployment succeeds

7. **Set Token Validity**: Use appropriate validity periods for PAT
   tokens and update them before they expire

8. **Document Custom Workflows**: Add README files to your
   workflow-deployment repository explaining custom workflows

## Examples

### Example 1: Single Project with No Overlays

```json
{
  "PAT_TOKENS_JSON": [
    {"github_org": "my-org", "github_token": "github_pat_XXX"}
  ],
  "DEPLOY_CONFIG_JSON": [
    {
      "github_username": "myuser",
      "projects": [
        {
          "project": "My Project",
          "slug": "myproject",
          "server": "gerrit.example.org",
          "github_org": "my-org",
          "projects": "project1, project2",
          "deploy_repo": "",
          "skeleton_repo": "my-org/workflows-skeleton",
          "prune": "true"
        }
      ]
    }
  ]
}
```

Result: Mirrors Gerrit projects to GitHub and creates skeleton
repository with `.github` content.

### Example 2: Projects with Overlays

```json
{
  "PAT_TOKENS_JSON": [
    {"github_org": "org1", "github_token": "github_pat_AAA"},
    {"github_org": "org2", "github_token": "github_pat_BBB"}
  ],
  "DEPLOY_CONFIG_JSON": [
    {
      "github_username": "myuser",
      "projects": [
        {
          "project": "Project Alpha",
          "slug": "alpha",
          "server": "gerrit.alpha.org",
          "github_org": "org1",
          "projects": "core, plugins",
          "deploy_repo": "myuser/workflow-deployment",
          "skeleton_repo": "org1/alpha-workflows",
          "prune": "true"
        },
        {
          "project": "Project Beta",
          "slug": "beta",
          "server": "gerrit.beta.org",
          "github_org": "org2",
          "projects": "main",
          "deploy_repo": "myuser/workflow-deployment",
          "skeleton_repo": "org2/beta-workflows",
          "prune": "false"
        }
      ]
    }
  ]
}
```

Result: Mirrors both projects, creates separate skeleton repositories,
and applies overlays from workflow-deployment repository.

## Support

For issues or questions:

1. Check the workflow logs for detailed error messages
2. Review this usage guide and README.md
3. Verify your configuration matches the examples
4. Open an issue in the repository with:
   - Configuration (redact tokens)
   - Error messages from logs
   - Steps to reproduce
