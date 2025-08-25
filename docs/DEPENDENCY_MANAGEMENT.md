# Dependency Management Guide

This document explains the dependency management strategy for the AI Content Farm project.

## Overview

The project uses a standardized approach to dependency management across all containers to ensure:
- Version consistency across services
- Proper separation of production and test dependencies
- Automated version management and updates
- Reduced production container size and attack surface

## File Structure

Each container has the following dependency files:

```
containers/[service-name]/
├── requirements-prod.txt    # Production dependencies only
├── requirements-test.txt    # Test/development dependencies only
└── requirements.txt         # Legacy monolithic file (being phased out)
```

## Version Management

### Compatible Release Versioning

All dependencies use the `~=` (compatible release) operator:

```bash
# Good - allows patch updates, prevents breaking changes
fastapi~=0.116.1  # Allows 0.116.x, prevents 0.117.x

# Avoid - too restrictive
fastapi==0.116.1  # Locks to exact version

# Avoid - too permissive
fastapi>=0.116.1  # Could install breaking changes
```

### Shared Versions

Version consistency is maintained through:

1. **`shared-versions.toml`** - Central configuration file
2. **`scripts/standardize_versions.py`** - Automated synchronization

## Production vs Test Dependencies

### Production Dependencies (`requirements-prod.txt`)
- Core application dependencies
- Runtime libraries only
- No development or testing tools
- Used in Docker containers

### Test Dependencies (`requirements-test.txt`)
- Testing frameworks (pytest, etc.)
- Code quality tools (black, isort, mypy)
- Development utilities
- Only installed in CI/CD environments

## Tools and Scripts

### `scripts/standardize_versions.py`

Synchronizes dependency versions across all containers:

```bash
# Update all containers with shared versions
python scripts/standardize_versions.py
```

### `scripts/split_requirements.sh`

Separates monolithic requirements.txt into prod/test files:

```bash
# Split requirements for all containers
./scripts/split_requirements.sh

# Split requirements for specific container
./scripts/split_requirements.sh content-generator
```

## Docker Integration

All Dockerfiles now use production-only dependencies:

```dockerfile
# Install only production dependencies
COPY containers/[service]/requirements-prod.txt /tmp/
RUN pip install -r /tmp/requirements-prod.txt
```

## CI/CD Integration

GitHub Actions installs dependencies in this order:

1. Install pytest and basic test tools
2. Install production dependencies from `requirements-prod.txt`
3. Install test dependencies from `requirements-test.txt`

## Maintenance

### Adding New Dependencies

1. Add to appropriate section in `shared-versions.toml`
2. Run `python scripts/standardize_versions.py`
3. Test and commit changes

### Updating Versions

1. Update versions in `shared-versions.toml`
2. Run `python scripts/standardize_versions.py`
3. Test compatibility across all containers
4. Commit changes

### Best Practices

- Always use `~=` for version specifications
- Keep production dependencies minimal
- Update shared versions centrally
- Test changes across all containers
- Document any container-specific requirements

## Migration Status

- ✅ All containers have split requirements files
- ✅ All Dockerfiles updated to use production-only deps
- ✅ GitHub Actions updated for proper test dependency installation
- ✅ Version standardization complete across all services
- ✅ Automated tooling in place for maintenance

## Related Documentation

- [Version Standardization Summary](VERSION_STANDARDIZATION_SUMMARY.md)
- [Container Development Standards](CONTAINER_DEVELOPMENT_STANDARDS.md)
- [CI/CD Pipeline Design](CICD_PIPELINE_DESIGN.md)
