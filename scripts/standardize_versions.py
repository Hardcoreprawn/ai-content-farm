#!/usr/bin/env python3
"""
Script to standardize dependency versions across all containers.
Uses shared-versions.toml as the source of truth.
"""

import os
import sys
import toml
import re
from pathlib import Path


def load_shared_versions():
    """Load shared versions from TOML file."""
    shared_versions_file = Path("shared-versions.toml")
    if not shared_versions_file.exists():
        print(f"❌ shared-versions.toml not found!")
        sys.exit(1)

    with open(shared_versions_file, 'r') as f:
        versions = toml.load(f)

    return versions


def update_requirements_file(file_path, shared_versions, file_type):
    """Update a requirements file with standardized versions."""
    if not os.path.exists(file_path):
        return False

    print(f"📝 Processing {file_path}")

    with open(file_path, 'r') as f:
        lines = f.readlines()

    updated_lines = []
    changes_made = False

    for line in lines:
        line = line.strip()

        # Skip comments and empty lines
        if not line or line.startswith('#'):
            updated_lines.append(line + '\n')
            continue

        # Parse package[extras]~=version format
        match = re.match(r'^([a-zA-Z0-9_-]+)(\[[^\]]+\])?(~=|==|>=)(.+)$', line)
        if not match:
            updated_lines.append(line + '\n')
            continue

        package = match.group(1)
        extras = match.group(2) or ""
        operator = match.group(3)
        current_version = match.group(4)

        # Look for the package in shared versions
        new_version = None
        if file_type == 'prod' and package in shared_versions.get('production', {}):
            new_version = shared_versions['production'][package]
        elif file_type == 'test' and package in shared_versions.get('test', {}):
            new_version = shared_versions['test'][package]

        if new_version:
            # Ensure we use ~= for compatible release
            if not new_version.startswith('~='):
                new_version = f"~={new_version}" if not new_version.startswith(
                    '=') else new_version.replace('==', '~=', 1)

            new_line = f"{package}{extras}{new_version}"
            if new_line != line:
                print(f"  📌 {package}: {current_version} → {new_version}")
                changes_made = True
            updated_lines.append(new_line + '\n')
        else:
            # Keep original line but convert == to ~= if needed
            if operator == '==':
                new_line = line.replace('==', '~=', 1)
                if new_line != line:
                    print(f"  🔄 {package}: Converting == to ~= for compatibility")
                    changes_made = True
                updated_lines.append(new_line + '\n')
            else:
                updated_lines.append(line + '\n')

    if changes_made:
        with open(file_path, 'w') as f:
            f.writelines(updated_lines)
        return True

    return False


def main():
    shared_versions = load_shared_versions()
    print(f"📋 Loaded shared versions:")
    print(f"  🏭 Production: {len(shared_versions.get('production', {}))} packages")
    print(f"  🧪 Test: {len(shared_versions.get('test', {}))} packages")

    containers_dir = Path("containers")
    total_changes = 0

    for container_path in containers_dir.iterdir():
        if not container_path.is_dir():
            continue

        container_name = container_path.name
        print(f"\n🐳 Processing {container_name}")

        # Update production requirements
        prod_file = container_path / "requirements-prod.txt"
        if update_requirements_file(prod_file, shared_versions, 'prod'):
            total_changes += 1

        # Update test requirements
        test_file = container_path / "requirements-test.txt"
        if update_requirements_file(test_file, shared_versions, 'test'):
            total_changes += 1

        # Also check original requirements.txt and suggest splitting if needed
        req_file = container_path / "requirements.txt"
        if req_file.exists() and not prod_file.exists() and not test_file.exists():
            print(f"  ⚠️  Still has monolithic requirements.txt - consider splitting")

    print(f"\n✅ Standardization complete! Updated {total_changes} files")
    print("💡 All versions now use ~= for compatible releases")


if __name__ == "__main__":
    main()
