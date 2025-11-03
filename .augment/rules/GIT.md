---
type: "always_apply"
---

# Git Workflow & Versioning Guide

**Project**: Sentiment Analyzer v2 - Multilingual News Analysis System  
**Repository**: https://github.com/daadbina/sentiment-analyzer.git  
**Last Updated**: 2025-11-03

---

## Table of Contents

1. [Repository Structure](#repository-structure)
2. [Branch Strategy](#branch-strategy)
3. [Commit Conventions](#commit-conventions)
4. [Workflow: Feature Development](#workflow-feature-development)
5. [Workflow: Bug Fixes](#workflow-bug-fixes)
6. [Workflow: Releases](#workflow-releases)
7. [Workflow: Hotfixes](#workflow-hotfixes)
8. [Pull Request Process](#pull-request-process)
9. [Versioning & Tags](#versioning--tags)
10. [CI/CD Integration](#cicd-integration)
11. [Rollback Procedures](#rollback-procedures)
12. [Common Scenarios](#common-scenarios)

---

## Repository Structure

This is a **monorepo** containing 12 microservices with shared infrastructure:

```
sentiment-analyzer-v2/
├── crawler-service/                    # Phase 1: News crawling
├── ingest-validator-service/           # Phase 1: Data validation
├── canonicalizer-normalizer-service/   # Phase 2: URL normalization
├── ner-entity-linking-service/         # Phase 2: Entity extraction
├── embedding-service/                  # Phase 2: Multilingual embeddings
├── clustering-service/                 # Phase 2: Semantic grouping
├── feature-engineering-service/        # Phase 3: Feature computation
├── labeler-service/                    # Phase 3: Ground-truth ingestion
├── trainer-service/                    # Phase 3: Model training
├── predictor-service/                  # Phase 3: Online inference
├── neo4j-loader-service/               # Phase 4: Graph building
├── api-service/                        # Phase 5: REST API
├── shared/                             # Shared code & schemas
│   ├── schemas/                        # Avro schemas (Kafka contracts)
│   ├── utils/                          # Common utilities
│   └── constants/                      # Shared constants
├── k8s/                                # Kubernetes manifests
├── helm/                               # Helm charts (one per service)
├── docker-compose.yml                  # Local development
├── .github/workflows/                  # CI/CD pipelines
├── GIT.md                              # This file
├── Architecture.md                     # System architecture
├── Microservice.md                     # Service specifications
└── Task.md                             # Project requirements
```

**Key Principle**: All services are versioned together. A single tag `v1.0.0` represents the entire system at that point in time.

---

## Branch Strategy

This project uses a **modified Git Flow** optimized for microservices:

### Main Branches (Protected)

#### `main` (Production)
- **Purpose**: Production-ready code only
- **Protection Rules**:
  - ✅ Require pull request reviews (1 approval minimum)
  - ✅ Require status checks to pass (all CI/CD pipelines)
  - ✅ Require branches to be up to date before merging
  - ✅ No direct pushes allowed
  - ✅ Automatic deletion of head branches after merge
- **Deployment**: Automatically deployed to production on merge
- **Tagging**: Every merge to `main` must be tagged with semantic version (e.g., `v1.0.0`)

#### `develop` (Integration)
- **Purpose**: Integration branch for next release
- **Protection Rules**:
  - ✅ Require pull request reviews (1 approval minimum)
  - ✅ Require status checks to pass
  - ✅ No direct pushes allowed
- **Deployment**: Automatically deployed to staging on merge
- **Merging**: Only from feature/bugfix branches or release branches

### Supporting Branches

#### `feature/*` (Feature Development)
- **Naming**: `feature/{service-name}/{description}`
- **Examples**:
  - `feature/crawler-service/add-reuters-feed`
  - `feature/embedding-service/upgrade-labse-model`
  - `feature/api-service/add-prediction-endpoint`
- **Branch From**: `develop`
- **Merge Back To**: `develop` (via PR)
- **Deletion**: Delete after merge
- **Lifetime**: Days to weeks

#### `bugfix/*` (Bug Fixes)
- **Naming**: `bugfix/{service-name}/{issue-id}`
- **Examples**:
  - `bugfix/ingest-validator/issue-123-utf8-encoding`
  - `bugfix/crawler-service/issue-456-feed-timeout`
- **Branch From**: `develop`
- **Merge Back To**: `develop` (via PR)
- **Deletion**: Delete after merge
- **Lifetime**: Hours to days

#### `release/*` (Release Preparation)
- **Naming**: `release/v{MAJOR}.{MINOR}.{PATCH}`
- **Examples**:
  - `release/v1.0.0`
  - `release/v1.1.0`
- **Branch From**: `develop`
- **Merge Back To**: `main` (via PR) + `develop` (via PR)
- **Deletion**: Delete after merge
- **Lifetime**: Days (release testing phase)
- **Activities**:
  - Update version numbers in all services
  - Update CHANGELOG.md
  - Final testing and bug fixes
  - Create release notes

#### `hotfix/*` (Production Hotfixes)
- **Naming**: `hotfix/{service-name}/{issue-id}`
- **Examples**:
  - `hotfix/crawler-service/issue-789-feed-crash`
  - `hotfix/api-service/issue-790-auth-bypass`
- **Branch From**: `main`
- **Merge Back To**: `main` (via PR) + `develop` (via PR)
- **Deletion**: Delete after merge
- **Lifetime**: Hours (urgent production fixes)
- **Tagging**: Create patch version tag after merge to main

---

## Commit Conventions

This project uses **Conventional Commits** format for clear, semantic commit history.

### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Type

Must be one of:
- **feat**: A new feature
- **fix**: A bug fix
- **docs**: Documentation only changes
- **style**: Changes that don't affect code meaning (formatting, missing semicolons, etc.)
- **refactor**: Code change that neither fixes a bug nor adds a feature
- **perf**: Code change that improves performance
- **test**: Adding missing tests or correcting existing tests
- **chore**: Changes to build process, dependencies, or tooling
- **ci**: Changes to CI/CD configuration

### Scope

The scope specifies which service or component is affected:
- `crawler-service`
- `ingest-validator`
- `canonicalizer-normalizer`
- `ner-entity-linking`
- `embedding-service`
- `clustering-service`
- `feature-engineering`
- `labeler-service`
- `trainer-service`
- `predictor-service`
- `neo4j-loader`
- `api-service`
- `shared` (for shared utilities/schemas)
- `k8s` (for Kubernetes manifests)
- `helm` (for Helm charts)
- `docker-compose` (for local development)

### Subject

- Use imperative mood ("add" not "added" or "adds")
- Don't capitalize first letter
- No period (.) at the end
- Limit to 50 characters
- Be specific and descriptive

### Body

- Explain **what** and **why**, not how
- Wrap at 72 characters
- Separate from subject with blank line
- Use bullet points for multiple changes

### Footer

- Reference issue numbers: `Fixes #123`, `Closes #456`
- Breaking changes: `BREAKING CHANGE: description`

### Examples

**Simple feature:**
```
feat(crawler-service): add support for Reuters RSS feed

- Implement RSS parser for Reuters news feed
- Add feed URL to configuration
- Validate feed connectivity on startup

Fixes #42
```

**Bug fix:**
```
fix(ingest-validator): handle UTF-8 encoding edge case

The validator was failing on articles with mixed encoding.
Now properly detects and normalizes to UTF-8.

Fixes #123
```

**Documentation:**
```
docs(README): update deployment instructions

Add section on Kubernetes deployment and Helm charts.
```

**Breaking change:**
```
feat(shared): update Avro schema for news_raw topic

BREAKING CHANGE: Added required field 'publisher_id' to news_raw schema.
All producers must be updated to include this field.

Fixes #456
```

---

## Workflow: Feature Development

### Step 0: Understanding Branch Lifecycle

**When are branches created?**
- Feature branches are created from `develop` when starting new work
- Release branches are created from `develop` when preparing a release
- Hotfix branches are created from `main` when fixing production issues

**When are branches deleted?**
- **After merge to develop**: Feature and bugfix branches are deleted immediately after merging to develop
- **After merge to main**: Release and hotfix branches are deleted after merging to main
- **Automatic deletion**: GitHub is configured to automatically delete head branches after PR merge
- **Manual deletion**: If not auto-deleted, delete with: `git push origin --delete branch-name` and `git branch -d branch-name`

**Why delete branches?**
- Keeps repository clean and organized
- Prevents confusion about which branches are active
- Reduces clutter in branch list
- Follows Git Flow best practices

### Step 1: Create Feature Branch

```bash
# Update develop branch
git checkout develop
git pull origin develop

# Create feature branch
git checkout -b feature/crawler-service/add-reuters-feed
```

### Step 2: Develop & Commit

```bash
# Make changes
# ... edit files ...

# Stage changes
git add .

# Commit with conventional format
git commit -m "feat(crawler-service): add Reuters RSS feed support

- Implement RSS parser for Reuters
- Add feed configuration
- Add unit tests

Fixes #42"

# Continue making commits as needed
```

### Step 3: Keep Branch Updated

```bash
# Fetch latest changes
git fetch origin

# Rebase on develop (preferred over merge)
git rebase origin/develop

# If conflicts occur, resolve them and continue
git rebase --continue
```

### Step 4: Push & Create PR

```bash
# Push to remote
git push origin feature/crawler-service/add-reuters-feed

# Create PR on GitHub
# - Title: "feat(crawler-service): add Reuters RSS feed support"
# - Description: Include what, why, and testing notes
# - Link related issues
```

### Step 5: Code Review & Merge

- Address review comments
- Push additional commits (don't force-push after PR is open)
- Once approved, merge via GitHub UI (use "Squash and merge" for clean history)
- Delete branch after merge

---

## Workflow: Bug Fixes

### Step 1: Create Bugfix Branch

```bash
# Update develop branch
git checkout develop
git pull origin develop

# Create bugfix branch
git checkout -b bugfix/ingest-validator/issue-123-utf8-encoding
```

### Step 2: Fix & Test

```bash
# Make fix
# ... edit files ...

# Run tests
pytest ingest-validator-service/tests/

# Commit
git commit -m "fix(ingest-validator): handle UTF-8 encoding edge case

The validator was failing on articles with mixed encoding.
Now properly detects and normalizes to UTF-8.

Fixes #123"
```

### Step 3: Push & Create PR

```bash
git push origin bugfix/ingest-validator/issue-123-utf8-encoding

# Create PR on GitHub with clear description of the fix
```

---

## Workflow: Releases

### Step 1: Prepare Release Branch

```bash
# Update develop
git checkout develop
git pull origin develop

# Create release branch
git checkout -b release/v1.0.0
```

### Step 2: Update Version Numbers

Update version in all services:
- `crawler-service/setup.py` or `__version__`
- `ingest-validator-service/setup.py` or `__version__`
- ... (all 12 services)
- `docker-compose.yml` (image tags)
- `helm/*/Chart.yaml` (chart versions)

```bash
# Example for Python services
# Edit: service/src/__init__.py
__version__ = "1.0.0"

# Commit
git commit -m "chore(release): bump version to v1.0.0"
```

### Step 3: Update CHANGELOG

Update `CHANGELOG.md` in each service and root:

```markdown
## [1.0.0] - 2025-11-03

### Added
- Crawler service: Reuters RSS feed support
- Ingest validator: UTF-8 encoding validation
- API service: Prediction endpoint

### Fixed
- Embedding service: Model loading timeout
- Neo4j loader: Graph transaction failures

### Changed
- Updated Kafka schema for news_raw topic

### Deprecated
- Old embedding model v1 (use v2 instead)
```

```bash
git commit -m "docs(CHANGELOG): update for v1.0.0 release"
```

### Step 4: Create Release PR

```bash
git push origin release/v1.0.0

# Create PR to main with:
# - Title: "release: v1.0.0"
# - Description: Summary of changes, testing notes
```

### Step 5: Testing & Approval

- Run full integration tests
- Get approval from 2 reviewers
- Verify all CI/CD checks pass

### Step 6: Merge to Main

```bash
# Merge PR to main (use "Create a merge commit")
# This creates a merge commit that documents the release
```

### Step 7: Tag Release

```bash
# After merge to main
git checkout main
git pull origin main

# Create annotated tag
git tag -a v1.0.0 -m "Release version 1.0.0

Major features:
- Complete Phase 1 (crawler + validator)
- Phase 2 partial (canonicalizer, embedding)
- Phase 3 partial (feature engineering)

See CHANGELOG.md for details."

# Push tag
git push origin v1.0.0
```

### Step 8: Merge Back to Develop

```bash
# Create PR from main to develop
# This ensures develop has all release changes

git checkout develop
git pull origin develop
git merge main
git push origin develop

# Or create PR on GitHub and merge
```

### Step 9: Delete Release Branch

```bash
git push origin --delete release/v1.0.0
git branch -d release/v1.0.0
```

---

## Workflow: Hotfixes

### Step 1: Create Hotfix Branch

```bash
# Start from main (production)
git checkout main
git pull origin main

# Create hotfix branch
git checkout -b hotfix/crawler-service/issue-789-feed-crash
```

### Step 2: Fix & Test

```bash
# Make critical fix
# ... edit files ...

# Test thoroughly
pytest crawler-service/tests/

# Commit
git commit -m "fix(crawler-service): prevent feed timeout crash

The crawler was crashing when feeds took >30s to respond.
Now implements exponential backoff with max 60s timeout.

Fixes #789"
```

### Step 3: Create PR to Main

```bash
git push origin hotfix/crawler-service/issue-789-feed-crash

# Create PR to main with:
# - Title: "hotfix(crawler-service): prevent feed timeout crash"
# - Label: "hotfix"
# - Priority: High
```

### Step 4: Merge to Main & Tag

```bash
# After approval and merge to main
git checkout main
git pull origin main

# Create patch version tag
git tag -a v1.0.1 -m "Hotfix: prevent crawler feed timeout crash"
git push origin v1.0.1
```

### Step 5: Merge to Develop

```bash
# Ensure develop has the fix
git checkout develop
git pull origin develop
git merge main
git push origin develop

# Or create PR on GitHub
```

### Step 6: Cleanup

```bash
git push origin --delete hotfix/crawler-service/issue-789-feed-crash
git branch -d hotfix/crawler-service/issue-789-feed-crash
```

---

## Pull Request Process

### Before Creating PR

1. **Update your branch**:
   ```bash
   git fetch origin
   git rebase origin/develop  # or origin/main for hotfixes
   ```

2. **Run tests locally**:
   ```bash
   pytest {service}/tests/
   ```

3. **Run linters**:
   ```bash
   black {service}/src/
   flake8 {service}/src/
   ```

4. **Check for secrets**:
   ```bash
   git diff origin/develop | grep -E "password|token|key|secret"
   ```

### PR Title Format

```
<type>(<scope>): <subject>
```

Example: `feat(crawler-service): add Reuters RSS feed support`

### PR Description Template

```markdown
## Description
Brief description of changes.

## Type of Change
- [ ] New feature
- [ ] Bug fix
- [ ] Breaking change
- [ ] Documentation update

## Related Issues
Fixes #123
Related to #456

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests passed
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex logic
- [ ] Documentation updated
- [ ] No new warnings generated
- [ ] Tests pass locally
- [ ] No secrets committed

## Screenshots (if applicable)
```

### Review Requirements

| Branch | Min Approvals | Status Checks | Stale PR |
|--------|---------------|---------------|----------|
| main | 1 | All pass | Auto-dismiss |
| develop | 1 | All pass | Auto-dismiss |
| feature/* | 0 | All pass | N/A |
| hotfix/* | 1 | All pass | Auto-dismiss |

### Merge Strategy

- **Feature/Bugfix branches**: Use "Squash and merge" for clean history
- **Release branches**: Use "Create a merge commit" to document release
- **Hotfix branches**: Use "Create a merge commit" to document hotfix

---

## Versioning & Tags

### Semantic Versioning: MAJOR.MINOR.PATCH

- **MAJOR** (v2.0.0): Breaking changes across services
  - Schema changes that require migration
  - API changes that break clients
  - Database schema changes
  
- **MINOR** (v1.1.0): New features, backward compatible
  - New microservice added
  - New Kafka topic
  - New API endpoint
  - New optional fields in schemas
  
- **PATCH** (v1.0.1): Bug fixes, backward compatible
  - Bug fixes
  - Performance improvements
  - Documentation updates

### Tag Format

```bash
# Annotated tags (preferred)
git tag -a v1.0.0 -m "Release version 1.0.0

Description of major changes."

# Lightweight tags (for pre-releases)
git tag v1.0.0-rc1
```

### Pre-release Versions

For release candidates and beta versions:
- `v1.0.0-rc1` (release candidate 1)
- `v1.0.0-beta1` (beta 1)
- `v1.0.0-alpha1` (alpha 1)

### Version Lifecycle

```
v1.0.0-alpha1 → v1.0.0-beta1 → v1.0.0-rc1 → v1.0.0 (stable)
                                                    ↓
                                            v1.0.1 (patch)
                                            v1.1.0 (minor)
                                            v2.0.0 (major)
```

---

## CI/CD Integration

### Automated Checks on PR

All PRs automatically run:

1. **Unit Tests**: `pytest` for all affected services
2. **Linting**: `black`, `flake8`, `pylint`
3. **Type Checking**: `mypy` (if applicable)
4. **Schema Validation**: Avro schema compatibility checks
5. **Security Scan**: `bandit` for security issues
6. **Docker Build**: Build Docker images for changed services
7. **Integration Tests**: Run with Docker Compose

### Automated Deployment

- **Merge to develop**: Deploy to staging environment
- **Merge to main**: Deploy to production environment
- **Tag creation**: Trigger release pipeline

### Status Checks

All of these must pass before merge:
- ✅ Unit tests
- ✅ Integration tests
- ✅ Linting
- ✅ Schema validation
- ✅ Security scan
- ✅ Docker build

---

## Rollback Procedures

### Rollback Recent Commit (Not Yet Pushed)

```bash
# Undo last commit, keep changes
git reset --soft HEAD~1

# Undo last commit, discard changes
git reset --hard HEAD~1
```

### Rollback Pushed Commit

```bash
# Create new commit that reverts changes
git revert <commit-hash>
git push origin develop
```

### Rollback Merged PR

```bash
# Option 1: Revert the merge commit
git revert -m 1 <merge-commit-hash>
git push origin main

# Option 2: Create hotfix branch and fix properly
git checkout -b hotfix/fix-issue
# ... make proper fix ...
git push origin hotfix/fix-issue
# Create PR to main
```

### Rollback Production Deployment

```bash
# If v1.0.0 has critical issue:

# Option 1: Deploy previous version
kubectl set image deployment/crawler-service \
  crawler-service=sentiment-analyzer:v0.9.9

# Option 2: Create hotfix and deploy v1.0.1
git checkout -b hotfix/critical-issue
# ... fix ...
git push origin hotfix/critical-issue
# Create PR, merge, tag v1.0.1, deploy
```

---

## Workflow: Starting a New Microservice

### When to Create a New Microservice Branch

When implementing a new microservice (e.g., `embedding-service`, `clustering-service`), follow this workflow:

### Step 1: Create Feature Branch from Develop

```bash
# Update develop branch
git checkout develop
git pull origin develop

# Create feature branch for new microservice
git checkout -b feature/embedding-service/initial-implementation
```

### Step 2: Implement the Microservice

Create the complete microservice structure:
```
embedding-service/
├── src/                          # Source code
├── tests/                        # Test suite
├── schemas/                      # Avro schemas
├── k8s/                          # Kubernetes manifests
├── helm/                         # Helm charts
├── docker-compose.yml            # Local development
├── Dockerfile                    # Container image
├── requirements.txt              # Python dependencies
├── README.md                     # Service documentation
├── CHANGELOG.md                  # Service changelog
└── .gitignore                    # Service-specific ignores
```

### Step 3: Commit with Conventional Format

```bash
git add embedding-service/
git commit -m "feat(embedding-service): implement Phase 2 multilingual embeddings

- Implement embedding generation with multilingual models
- Support for 50+ languages
- Kafka consumer/producer integration
- Redis caching for performance
- Prometheus metrics and health checks
- Docker and Kubernetes deployment
- Comprehensive test suite

Implements Phase 2 embedding layer as per Architecture.md"
```

### Step 4: Push and Create PR

```bash
git push -u origin feature/embedding-service/initial-implementation

# Create PR on GitHub for code review
```

### Step 5: Merge to Develop

After approval:
```bash
# Merge via GitHub UI or:
git checkout develop
git pull origin develop
git merge feature/embedding-service/initial-implementation
git push origin develop

# Delete the feature branch
git push origin --delete feature/embedding-service/initial-implementation
git branch -d feature/embedding-service/initial-implementation
```

### Important Notes for New Microservices

1. **Always start from develop**: Never create feature branches from main
2. **Follow naming convention**: `feature/{service-name}/{description}`
3. **Include all components**: Dockerfile, Kubernetes manifests, Helm charts, tests
4. **Create CHANGELOG.md**: Document the initial implementation
5. **Create .gitignore**: Service-specific file exclusions
6. **Update root CHANGELOG.md**: Add entry for new service in root changelog
7. **Merge to develop first**: All services must be in develop before release
8. **Delete branch after merge**: Keep repository clean

---

## Common Scenarios

### Scenario 1: I Made a Commit to Wrong Branch

```bash
# You committed to feature/wrong-branch but meant develop

# Create correct branch
git checkout -b feature/correct-branch

# Go back to wrong branch
git checkout feature/wrong-branch

# Reset to before your commit
git reset --hard origin/feature/wrong-branch

# Go to correct branch
git checkout feature/correct-branch

# Your commits are now on correct branch
```

### Scenario 2: I Need to Update My PR with Latest Develop

```bash
git fetch origin
git rebase origin/develop

# If conflicts, resolve them
# Then continue
git rebase --continue

# Force push (only safe before PR is merged)
git push origin feature/my-feature --force-with-lease
```

### Scenario 3: I Accidentally Committed Secrets

```bash
# IMMEDIATELY revoke the secret in your system

# Remove from git history
git filter-branch --tree-filter 'rm -f path/to/secret' HEAD

# Force push
git push origin --force-with-lease

# Notify team
```

### Scenario 4: I Need to Cherry-pick a Commit from Another Branch

```bash
# Get commit hash from other branch
git log feature/other-branch --oneline

# Cherry-pick it
git cherry-pick <commit-hash>

# If conflicts, resolve and continue
git cherry-pick --continue
```

### Scenario 5: Release is Ready but Develop Has New Commits

```bash
# You're on release/v1.0.0 but develop has new commits

# Option 1: Include new commits (if they're stable)
git rebase origin/develop

# Option 2: Keep release isolated (recommended)
# Just merge release/v1.0.0 to main
# Then merge main back to develop
```

### Scenario 6: I Need to Undo a Merge

```bash
# Merge was bad, need to undo
git revert -m 1 <merge-commit-hash>
git push origin develop

# This creates a new commit that undoes the merge
```

---

## Best Practices

### ✅ DO

- ✅ Write clear, descriptive commit messages
- ✅ Keep commits small and focused
- ✅ Rebase before pushing (keep history clean)
- ✅ Test locally before pushing
- ✅ Review your own code first
- ✅ Use feature branches for all work
- ✅ Keep branches up to date with develop
- ✅ Delete branches after merge
- ✅ Tag all releases
- ✅ Document breaking changes

### ❌ DON'T

- ❌ Commit directly to main or develop
- ❌ Force push to main or develop
- ❌ Commit secrets or credentials
- ❌ Make huge commits with multiple unrelated changes
- ❌ Use vague commit messages ("fix stuff", "update")
- ❌ Leave stale branches
- ❌ Merge without tests passing
- ❌ Skip code review
- ❌ Rewrite history after PR is open
- ❌ Ignore CI/CD failures

---

## Questions?

For questions about this workflow, please:
1. Check this document first
2. Ask in team Slack/Discord
3. Create an issue on GitHub

---

**Last Updated**: 2025-11-03  
**Maintained By**: Development Team  
**Version**: 1.0

