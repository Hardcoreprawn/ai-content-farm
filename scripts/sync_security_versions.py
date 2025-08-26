#!/usr/bin/env python3
"""
Script to sync Security tool versions from shared-versions.toml to all configuration files.
This ensures all Safety configurations stay in sync.
"""

import os
import re
import sys
from pathlib import Path

try:
    import toml
except ImportError:
    print("❌ toml package not found. Install with: pip install toml")
    sys.exit(1)


def load_security_versions():
    """Load security tool versions from shared-versions.toml."""
    shared_versions_file = Path("config/shared-versions.toml")
    if not shared_versions_file.exists():
        print(f"❌ config/shared-versions.toml not found!")
        sys.exit(1)

    with open(shared_versions_file, "r") as f:
        versions = toml.load(f)

    security_versions = versions.get("security", {})
    if not security_versions:
        print("❌ No [security] section found in shared-versions.toml")
        sys.exit(1)

    return security_versions


def update_requirements_files(security_versions):
    """Update requirements.txt and requirements-dev.txt files."""
    safety_version = security_versions.get("safety", "~=3.2.7")

    files_to_update = ["requirements-dev.txt", "requirements.txt"]

    updated_count = 0

    for file_path in files_to_update:
        if not os.path.exists(file_path):
            continue

        print(f"📝 Checking {file_path}")

        with open(file_path, "r") as f:
            content = f.read()

        # Update safety version
        pattern = r"^safety~?=[\d.]+.*$"
        replacement = f"safety{safety_version}     # Security vulnerability scanning"

        new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

        if new_content != content:
            with open(file_path, "w") as f:
                f.write(new_content)
            print(f"✅ Updated Safety version in {file_path}")
            updated_count += 1
        else:
            print(f"ℹ️  {file_path} already up to date")

    return updated_count


def update_github_actions(security_versions):
    """Update GitHub Actions files that might have hardcoded Safety versions."""
    safety_version = security_versions.get("safety", "~=3.2.7")

    # Find all GitHub Actions files
    actions_files = []
    github_dir = Path(".github")
    if github_dir.exists():
        actions_files.extend(github_dir.rglob("*.yml"))
        actions_files.extend(github_dir.rglob("*.yaml"))

    updated_count = 0

    for file_path in actions_files:
        if not file_path.is_file():
            continue

        try:
            with open(file_path, "r") as f:
                content = f.read()
        except Exception as e:
            print(f"⚠️  Could not read {file_path}: {e}")
            continue

        # Look for hardcoded safety versions (but skip our centralized config action)
        if "safety-config" in str(file_path):
            continue

        # Update pip install safety commands
        pattern = r'pip install.*["\']safety~?=[\d.]+["\']'
        replacement = f'pip install "safety{safety_version}"'

        new_content = re.sub(pattern, replacement, content)

        if new_content != content:
            with open(file_path, "w") as f:
                f.write(new_content)
            print(f"✅ Updated Safety version in {file_path}")
            updated_count += 1

    return updated_count


def update_makefile(security_versions):
    """Update Makefile with correct Safety version."""
    safety_version = security_versions.get("safety", "~=3.2.7")
    makefile_path = Path("Makefile")

    if not makefile_path.exists():
        return 0

    print(f"📝 Checking Makefile")

    with open(makefile_path, "r") as f:
        content = f.read()

    # Update safety version in pip install commands
    pattern = r'pip install -q ["\']safety~?=[\d.]+["\']'
    replacement = f'pip install -q "safety{safety_version}"'

    new_content = re.sub(pattern, replacement, content)

    if new_content != content:
        with open(makefile_path, "w") as f:
            f.write(new_content)
        print(f"✅ Updated Safety version in Makefile")
        return 1
    else:
        print(f"ℹ️  Makefile already up to date")
        return 0


def main():
    """Main function to sync all Safety configurations."""
    print("🔧 Syncing Security tool versions from shared-versions.toml...")

    # Load versions from central config
    security_versions = load_security_versions()
    safety_version = security_versions.get("safety", "~=3.2.7")

    print(f"📋 Target Safety version: {safety_version}")

    # Update different types of files
    total_updated = 0
    total_updated += update_requirements_files(security_versions)
    total_updated += update_github_actions(security_versions)
    total_updated += update_makefile(security_versions)

    if total_updated > 0:
        print(
            f"✅ Successfully updated {total_updated} files with Safety version {safety_version}"
        )
        print(
            "💡 Consider running standardize_versions.py to sync other dependencies too"
        )
    else:
        print("ℹ️  All files already up to date with central Safety configuration")

    return 0


if __name__ == "__main__":
    sys.exit(main())
