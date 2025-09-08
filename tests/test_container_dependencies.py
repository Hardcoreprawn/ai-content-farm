"""
Test Container Dependencies

Validates that all containers have the required dependencies properly configured
to prevent deployment failures due to missing packages.

This test specifically prevents issues like missing azure-identity in site-generator
that caused the "cannot import name 'BlobStorageClient'" error.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Set

import pytest

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestContainerDependencies:
    """Test suite for container dependency validation."""

    @pytest.fixture
    def container_paths(self) -> List[Path]:
        """Get all container directories."""
        containers_dir = project_root / "containers"
        return [
            path
            for path in containers_dir.iterdir()
            if path.is_dir() and path.name != "__pycache__" and path.name != "base"
        ]

    @pytest.fixture
    def azure_requirements(self) -> Set[str]:
        """Define required Azure packages for containers using blob storage."""
        return {
            "azure-storage-blob",
            "azure-identity",
        }  # azure-core is a transitive dependency

    def get_requirements_file(self, container_path: Path) -> Path:
        """Get the requirements file for a container."""
        # Check for production requirements first, then fall back to general requirements
        prod_req = container_path / "requirements-prod.txt"
        general_req = container_path / "requirements.txt"

        if prod_req.exists():
            return prod_req
        elif general_req.exists():
            return general_req
        else:
            raise FileNotFoundError(
                f"No requirements file found for {container_path.name}"
            )

    def parse_requirements(self, req_file: Path) -> Dict[str, str]:
        """Parse requirements file and return package name to version mapping."""
        requirements = {}

        with open(req_file, "r") as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if not line or line.startswith("#"):
                    continue

                # Handle version specifications
                if "==" in line:
                    package, version = line.split("==", 1)
                elif "~=" in line:
                    package, version = line.split("~=", 1)
                elif ">=" in line:
                    package, version = line.split(">=", 1)
                elif "<=" in line:
                    package, version = line.split("<=", 1)
                elif ">" in line:
                    package, version = line.split(">", 1)
                elif "<" in line:
                    package, version = line.split("<", 1)
                else:
                    package = line
                    version = "any"

                requirements[package.strip()] = version.strip()

        return requirements

    def uses_blob_storage(self, container_path: Path) -> bool:
        """Check if a container uses blob storage by examining its code."""
        # Check Python files for blob storage imports
        python_files = list(container_path.glob("*.py"))

        for py_file in python_files:
            try:
                with open(py_file, "r") as f:
                    content = f.read()
                    if any(
                        pattern in content
                        for pattern in [
                            "BlobStorageClient",
                            "from libs import BlobStorageClient",
                            "azure.storage.blob",
                            "DefaultAzureCredential",
                            "ManagedIdentityCredential",
                        ]
                    ):
                        return True
            except (UnicodeDecodeError, PermissionError):
                # Skip files that can't be read
                continue

        return False

    def test_all_containers_have_requirements_file(self, container_paths: List[Path]):
        """Test that all containers have a requirements file."""
        for container_path in container_paths:
            try:
                req_file = self.get_requirements_file(container_path)
                assert (
                    req_file.exists()
                ), f"Container {container_path.name} is missing requirements file"
            except FileNotFoundError as e:
                pytest.fail(str(e))

    def test_blob_storage_containers_have_azure_dependencies(
        self, container_paths: List[Path], azure_requirements: Set[str]
    ):
        """Test that containers using blob storage have required Azure dependencies."""
        for container_path in container_paths:
            if not self.uses_blob_storage(container_path):
                continue

            try:
                req_file = self.get_requirements_file(container_path)
                requirements = self.parse_requirements(req_file)
                required_packages = set(requirements.keys())

                missing_packages = azure_requirements - required_packages

                assert not missing_packages, (
                    f"Container {container_path.name} uses blob storage but is missing "
                    f"required Azure packages: {missing_packages}. "
                    f"Required: {azure_requirements}. "
                    f"Found: {required_packages & azure_requirements}"
                )

            except FileNotFoundError as e:
                pytest.fail(f"Container {container_path.name}: {e}")

    def test_site_generator_azure_identity_dependency(
        self, container_paths: List[Path]
    ):
        """Specific test for the site-generator azure-identity issue that was fixed."""
        site_generator_path = None
        for container_path in container_paths:
            if container_path.name == "site-generator":
                site_generator_path = container_path
                break

        assert site_generator_path is not None, "site-generator container not found"

        req_file = self.get_requirements_file(site_generator_path)
        requirements = self.parse_requirements(req_file)

        # Ensure azure-identity is present since site-generator uses BlobStorageClient
        assert "azure-identity" in requirements, (
            "site-generator is missing azure-identity dependency. "
            "This causes 'cannot import name BlobStorageClient' errors in Azure. "
            f"Current requirements: {list(requirements.keys())}"
        )

        assert (
            "azure-storage-blob" in requirements
        ), "site-generator is missing azure-storage-blob dependency"

    def test_requirements_files_are_parseable(self, container_paths: List[Path]):
        """Test that all requirements files can be parsed without errors."""
        for container_path in container_paths:
            try:
                req_file = self.get_requirements_file(container_path)
                requirements = self.parse_requirements(req_file)

                # Basic validation - should have at least some packages
                assert (
                    len(requirements) > 0
                ), f"Requirements file for {container_path.name} appears to be empty"

                # Check for common issues
                for package, version in requirements.items():
                    assert (
                        package
                    ), f"Empty package name in {container_path.name} requirements"
                    assert not package.startswith(
                        "-"
                    ), f"Invalid package name '{package}' in {container_path.name} requirements"

            except FileNotFoundError as e:
                pytest.fail(f"Container {container_path.name}: {e}")
            except Exception as e:
                pytest.fail(
                    f"Failed to parse requirements for {container_path.name}: {e}"
                )

    def test_azure_package_versions_are_compatible(self, container_paths: List[Path]):
        """Test that Azure package versions are compatible across containers."""
        azure_versions = {}

        for container_path in container_paths:
            if not self.uses_blob_storage(container_path):
                continue

            try:
                req_file = self.get_requirements_file(container_path)
                requirements = self.parse_requirements(req_file)

                for package in ["azure-storage-blob", "azure-identity", "azure-core"]:
                    if package in requirements:
                        version = requirements[package]
                        if package not in azure_versions:
                            azure_versions[package] = {}
                        azure_versions[package][container_path.name] = version

            except FileNotFoundError:
                continue

        # Check for version conflicts
        for package, container_versions in azure_versions.items():
            unique_versions = set(v for v in container_versions.values() if v != "any")
            if len(unique_versions) > 1:
                pytest.fail(
                    f"Version conflict for {package}: {container_versions}. "
                    f"All containers should use the same Azure package versions."
                )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
