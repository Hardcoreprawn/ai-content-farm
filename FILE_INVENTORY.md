# File Inventory & Purpose

This document provides a comprehensive overview of every file in the project, its purpose, status, and relationships.

## Project Root

### Configuration Files
| File | Purpose | Status | Notes |
|------|---------|--------|-------|
| `.gitignore` | Git ignore patterns | ✅ Complete | Excludes build artifacts, credentials, temp files |
| `.markdownlint.json` | Markdown linting rules | ✅ Complete | Ensures consistent documentation formatting |
| `requirements.txt` | Root Python dependencies | ✅ Complete | For local development: requests, mkdocs |
| `Makefile` | Build and deployment automation | ✅ Complete | Main interface for all project operations |
| `mkdocs.yml` | Documentation site configuration | ✅ Complete | For future documentation website |

### Documentation Files
| File | Purpose | Status | Notes |
|------|---------|--------|-------|
| `README.md` | Project overview and getting started | ✅ Complete | Main entry point for new users |
| `DESIGN.md` | System architecture and design | ✅ Complete | Comprehensive technical design documentation |
| `PROJECT_LOG.md` | Development history and decisions | ✅ Complete | Historical record of project evolution |
| `AGENT_INSTRUCTIONS.md` | AI assistant context and instructions | ✅ Complete | Context for AI development assistance |

## Azure Function (`azure-function-deploy/`)

### Function Code
| File | Purpose | Status | Notes |
|------|---------|--------|-------|
| `GetHotTopics/__init__.py` | Main Azure Function code | 🔄 Needs Reddit API | Timer-triggered Reddit scraper |
| `GetHotTopics/function.json` | Function configuration | ✅ Complete | Timer trigger, bindings configuration |
| `host.json` | Azure Functions host configuration | ✅ Complete | Runtime settings, logging configuration |
| `requirements.txt` | Azure Function dependencies | 🔄 Ready for PRAW | Includes azure-functions, azure-storage-blob, praw |

**Dependencies**:
- Azure Functions runtime (azure-functions)
- Azure Storage SDK (azure-storage-blob)
- Azure Identity (azure-identity)
- Azure Key Vault (azure-keyvault-secrets)
- Reddit API wrapper (praw)
- HTTP requests (requests)

## Local Development (`content_wombles/`)

### Active Scripts
| File | Purpose | Status | Notes |
|------|---------|--------|-------|
| `get-hot-topics.py` | Local Reddit scraper | ✅ Fully functional | Works with anonymous Reddit API calls |
| `womble_status.py` | Data monitoring and analysis | ✅ Fully functional | Shows collection status, data samples |
| `run_all_wombles.py` | Multi-womble executor | ✅ Functional | Runs all available womble scripts |

**Features**:
- Timestamped file output
- Comprehensive source tracking (external URLs + Reddit permalinks)
- Author and engagement metrics
- Error handling and logging

## Infrastructure (`infra/`)

### Terraform Configuration
| File | Purpose | Status | Notes |
|------|---------|--------|-------|
| `main.tf` | Primary infrastructure definition | ✅ Deployed | All Azure resources, managed identity, RBAC |
| `providers.tf` | Terraform provider configuration | ✅ Complete | Azure provider with required features |
| `variables.tf` | Input variable definitions | ✅ Complete | Configurable resource settings |
| `outputs.tf` | Output value definitions | ✅ Complete | Resource IDs and connection info |
| `README.md` | Infrastructure documentation | ✅ Complete | Deployment instructions |

### State Files (Ignored by Git)
| File | Purpose | Status | Notes |
|------|---------|--------|-------|
| `terraform.tfstate` | Current infrastructure state | ✅ Active | Tracks deployed resources |
| `terraform.tfstate.backup` | Previous state backup | ✅ Active | Automatic backup for rollback |

**Deployed Resources**:
- Resource Group: `hot-topics-rg`
- Function App: `hot-topics-func`
- Storage Account: `hottopicsstorageib91ea`
- Storage Container: `hot-topics`
- Key Vault: `hottopicskv{suffix}`
- App Service Plan: `hot-topics-plan`

## Documentation (`docs/`)

### Content Structure
| File/Directory | Purpose | Status | Notes |
|----------------|---------|--------|-------|
| `index.md` | Documentation homepage | ✅ Basic | Main documentation entry point |
| `articles/` | Generated content directory | ✅ Ready | Will contain processed articles |
| `articles/2025-07-24-sample-topic.md` | Sample article | ✅ Example | Template for future content |

## Static Site (`site/`)

### Frontend Configuration
| File | Purpose | Status | Notes |
|------|---------|--------|-------|
| `package.json` | Node.js dependencies | ✅ Complete | Eleventy static site generator |
| `src/base.njk` | HTML template | ✅ Basic | Base layout for generated pages |
| `src/index.md` | Homepage content | ✅ Basic | Site homepage markdown |
| `src/generate_articles.py` | Article generator | ✅ Ready | Python script to process topics into articles |

## Output Data (`output/`)

### Generated Content
| Pattern | Purpose | Status | Notes |
|---------|---------|--------|-------|
| `YYYYMMDD_HHMMSS_reddit_*.json` | Local topic collections | ✅ Active | Generated by local wombles |

**Sample Files**:
- `20250724_120628_reddit_technology.json`
- `20250724_121245_reddit_programming.json`
- etc.

**Data Retention**: Currently keeping 14 most recent files per cleanup

## Development Container (`.devcontainer/`)

### Container Configuration
| File | Purpose | Status | Notes |
|------|---------|--------|-------|
| `devcontainer.json` | VS Code dev container config | ✅ Complete | Development environment definition |
| `Dockerfile` | Container image definition | ✅ Complete | Base image with all required tools |

**Included Tools**:
- Python 3.11 with pip
- Node.js with npm
- Azure CLI
- Terraform
- Git
- Essential development tools

## CI/CD (`.github/workflows/`)

### GitHub Actions
| File | Purpose | Status | Notes |
|------|---------|--------|-------|
| `build-and-deploy.yml` | Main deployment pipeline | ✅ Ready | Automated build and deploy |
| `checkov.yml` | Security scanning | ✅ Active | Infrastructure security validation |

## File Relationships

### Data Flow Dependencies
```
content_wombles/get-hot-topics.py → output/*.json
azure-function-deploy/GetHotTopics/__init__.py → Azure Blob Storage
infra/main.tf → All Azure resources
Makefile → All deployment processes
```

### Configuration Dependencies
```
azure-function-deploy/requirements.txt → GetHotTopics/__init__.py
infra/main.tf → azure-function-deploy/ (deployment target)
.devcontainer/ → All development activities
```

## Maintenance Notes

### Regular Updates Needed
- `azure-function-deploy/requirements.txt`: Keep Azure SDK versions current
- `infra/providers.tf`: Update Azure provider version
- `output/`: Periodic cleanup of old files
- `.devcontainer/`: Update base images and tool versions

### Clean-up Targets
- Temporary files in `output/` (managed by Makefile clean target)
- Build artifacts (`.python_packages`, `__pycache__`)
- Node modules in `site/`

### Security-Sensitive Files
- Any files containing credentials (must be in `.gitignore`)
- `terraform.tfstate*` (contains resource IDs but no secrets)
- Azure Function app settings (managed via Terraform)
