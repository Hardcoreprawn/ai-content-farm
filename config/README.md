# Configuration Directory

This directory contains all project configuration files to keep the root directory organized.

## Files in this directory:

### Python Configuration
- **`pytest.ini`** - pytest configuration (primary config)
- **`conftest.py`** - pytest fixtures and common test utilities 
- **`.flake8`** - Python code style and error checking
- **`.isort.cfg`** - Python import sorting configuration

### Security & Quality
- **`.semgrep.yml`** - Semgrep static analysis rules
- **`.semgrepignore`** - Files/patterns to ignore in Semgrep scans
- **`.checkov.yml`** - Infrastructure as Code security scanning

### Linting & Documentation
- **`.yamllint.yml`** - YAML file linting configuration  
- **`.markdownlint.json`** - Markdown linting rules

### Project Management
- **`shared-versions.toml`** - Centralized dependency version management
- **`actionlint`** - GitHub Actions workflow linter binary

## Tool Configuration

Most tools automatically discover their config files in this location when run from the project root:

- **pytest**: Uses the root `pytest.ini` which points to `config/pytest.ini`
- **flake8**: Uses `--config config/.flake8` or `setup.cfg` 
- **isort**: Uses `--settings-path config/.isort.cfg` or automatic discovery
- **yamllint**: Explicitly referenced in Makefile: `-c config/.yamllint.yml`
- **semgrep**: Uses `--config config/.semgrep.yml` in CI/CD

## Usage

When adding new configuration files:
1. Place them in this `config/` directory
2. Update any scripts or Makefile targets that reference them
3. Test that tools can find the config files correctly
4. Update this README to document the new files

## Integration with Root Directory

Some configuration still remains in the root directory for technical reasons:
- `.gitignore` - Must be in repository root
- `.pre-commit-config.yaml` - Expected in root by pre-commit
- `docker-compose.yml` - Docker Compose expects this in project root
- `Makefile` - Build tool, typically expected in root
- `.env*` - Environment files, often expected in root
