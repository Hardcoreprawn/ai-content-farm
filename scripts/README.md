# Scripts Directory

This directory contains utility scripts for the AI Content Farm project.

## 🔧 Development Scripts

### Environment Setup
- **`setup-local-dev.sh`** - Initialize local development environment with Docker and dependencies
- **`setup-keyvault.sh`** - Configure Azure Key Vault integration for secure credential management

### Security & Quality Assurance
- **`run-semgrep.sh`** - Standardized security scanning with Semgrep (ensures consistency between local dev and CI/CD)
- **`validate-security-consistency.sh`** - Validates that local and CI/CD security scans produce identical results

### Pipeline Operations
- **`run_pipeline.sh`** - Execute the complete content processing pipeline manually
- **`start-event-driven-pipeline.sh`** - Start the event-driven pipeline with automatic triggers
- **`test-pipeline.sh`** - Run comprehensive pipeline tests and validation

## 🐍 Python Utilities

### Content Processing
- **`generate_markdown.py`** - Convert processed content to markdown format for static site generation
- **`process_live_content.py`** - Process live content feeds and real-time data sources
- **`cms_integration.py`** - Integrate with external CMS systems and content management platforms

### Operations
- **`cost-calculator.py`** - Calculate and monitor Azure resource costs for the project

## 📖 Usage Examples

### Quick Setup
```bash
# Initialize development environment
./scripts/setup-local-dev.sh

# Start the complete pipeline
./scripts/run_pipeline.sh

# Test everything is working
./scripts/test-pipeline.sh
```

### Content Generation
```bash
# Generate markdown from processed content
python scripts/generate_markdown.py --input output/processed_content.json

# Process live content feeds  
python scripts/process_live_content.py --sources reddit,hackernews
```

### Monitoring
```bash
# Check Azure costs
python scripts/cost-calculator.py --subscription-id YOUR_SUB_ID
```

## 🚨 Important Notes

- **Make scripts executable**: Run `chmod +x scripts/*.sh` after cloning
- **Environment variables**: Ensure required environment variables are set before running scripts
- **Dependencies**: Some scripts require specific Python packages or Azure CLI tools
- **Permissions**: Azure scripts require appropriate Azure subscriptions and permissions

## �️ Security Scanning Consistency

The project ensures consistent security scanning results between local development and CI/CD:

### Local Development
```bash
# Run standardized security scan
./scripts/run-semgrep.sh

# Or use Makefile target
make scan-python

# Validate consistency
./scripts/validate-security-consistency.sh
```

### CI/CD Pipeline
The GitHub Actions pipeline uses the same standardized `run-semgrep.sh` script, ensuring identical:
- Semgrep rules and configuration (`--config=auto`)
- Output formats (JSON for counting, SARIF for GitHub integration)
- Container images (`semgrep/semgrep:latest`)
- Scanning parameters and exclusions

### Output Files
Both local and CI/CD generate consistent results in:
- `security-results/semgrep-results.json` - Detailed JSON format for local analysis
- `security-results/semgrep.sarif` - SARIF format for GitHub Security tab integration

## �🔄 Maintenance

When adding new scripts:
1. Follow existing naming conventions
2. Add appropriate documentation and usage examples
3. Update this README with the new script information
4. Ensure scripts are tested and working before committing

---
**Last Updated**: August 18, 2025
