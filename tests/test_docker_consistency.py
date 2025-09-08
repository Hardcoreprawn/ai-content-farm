#!/usr/bin/env python3
"""
Test Docker Consistency

Validates that all containers have consistent Docker setup:
1. Each container has exactly one Dockerfile
2. All Dockerfiles have proper multi-stage builds
3. Production targets are defined
4. No obsolete Dockerfile variants exist
"""

import os
import subprocess
from pathlib import Path

import pytest


def test_docker_file_consistency():
    """Test that each container has exactly one Dockerfile with production target."""
    containers_dir = Path("containers")

    # Get all container directories (exclude base)
    container_dirs = [
        d
        for d in containers_dir.iterdir()
        if d.is_dir() and d.name not in ["base", "__pycache__"]
    ]

    print(f"Found {len(container_dirs)} containers to validate")

    errors = []

    for container_dir in container_dirs:
        container_name = container_dir.name
        print(f"\n=== Validating {container_name} ===")

        # Check for standard Dockerfile
        dockerfile = container_dir / "Dockerfile"
        if not dockerfile.exists():
            errors.append(f"{container_name}: Missing standard Dockerfile")
            continue

        # Check for obsolete Dockerfile variants
        obsolete_files = [
            "Dockerfile.production",
            "Dockerfile.development",
            "Dockerfile.test",
        ]

        for obsolete_file in obsolete_files:
            obsolete_path = container_dir / obsolete_file
            if obsolete_path.exists():
                errors.append(
                    f"{container_name}: Obsolete file {obsolete_file} should be removed"
                )

        # Validate Dockerfile content
        dockerfile_content = dockerfile.read_text()

        # Check for multi-stage build with production target
        if (
            "FROM base AS production" not in dockerfile_content
            and "FROM python:" not in dockerfile_content
        ):
            errors.append(
                f"{container_name}: Dockerfile missing 'FROM base AS production' target"
            )

        # Check for proper USER directive (Azure security requirement)
        if "USER app" not in dockerfile_content:
            errors.append(
                f"{container_name}: Dockerfile missing 'USER app' directive for Azure security"
            )

        # Check for EXPOSE directive
        if "EXPOSE" not in dockerfile_content:
            errors.append(f"{container_name}: Dockerfile missing EXPOSE directive")

        print(f"✓ {container_name}: Standard Dockerfile found")

    # Report results
    if errors:
        print("\n❌ Docker consistency errors found:")
        for error in errors:
            print(f"  - {error}")
        raise AssertionError(f"Found {len(errors)} Docker consistency issues")
    else:
        print(f"\n✅ All {len(container_dirs)} containers have consistent Docker setup")


def test_build_system_consistency():
    """Test that build and deploy systems use the same Dockerfile pattern."""
    print("\n=== Testing Build System Consistency ===")

    # Check build action uses standard Dockerfile
    build_action = Path(".github/actions/build-and-push-container/action.yml")
    if build_action.exists():
        build_content = build_action.read_text()
        if 'dockerfile_path="$container_dir/Dockerfile"' not in build_content:
            raise AssertionError("Build action doesn't use standard Dockerfile path")
        print("✓ Build action uses standard Dockerfile")

    # Check deploy action uses consistent pattern
    deploy_action = Path(".github/actions/deploy-containers/action.yml")
    if deploy_action.exists():
        deploy_content = deploy_action.read_text()
        if "Dockerfile --target production" not in deploy_content:
            raise AssertionError(
                "Deploy action doesn't use standard multi-stage build pattern"
            )
        print("✓ Deploy action uses standard multi-stage build")

    print("✅ Build and deploy systems are consistent")


def test_containers_base_is_clean():
    """Test that containers/base only contains essential shared files."""
    base_dir = Path("containers/base")
    if not base_dir.exists():
        pytest.skip("containers/base directory doesn't exist")

    # Get all files in the base directory
    base_files = list(base_dir.rglob("*"))
    base_file_names = [f.name for f in base_files if f.is_file()]

    # Only allow essential shared files
    allowed_files = {
        "requirements-common.txt",  # Shared dependencies used by all containers
    }

    unexpected_files = set(base_file_names) - allowed_files
    assert (
        not unexpected_files
    ), f"containers/base contains unexpected files: {unexpected_files}. Only {allowed_files} should be present."


if __name__ == "__main__":
    print("🐳 Testing Docker Consistency\n")

    # Change to repository root
    repo_root = Path(__file__).parent.parent
    os.chdir(repo_root)

    try:
        test_docker_file_consistency()
        test_build_system_consistency()
        test_containers_base_is_clean()
        print("\n🎉 All Docker consistency tests passed!")
    except Exception as e:
        print(f"\n💥 Test failed: {e}")
        exit(1)
