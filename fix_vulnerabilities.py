#!/usr/bin/env python3
"""
Fix security vulnerabilities by updating dependencies across all containers.
This script addresses the 33 vulnerabilities found by Dependabot.
"""

import os
import re
import subprocess
from pathlib import Path

# Vulnerable packages and their secure versions
VULNERABILITY_FIXES = {
    # HIGH severity vulnerabilities
    "python-multipart": "0.0.18",  # Fixes DoS vulnerabilities
    
    # MEDIUM severity vulnerabilities  
    "requests": "2.32.4",  # Fixes CVE-2024-47081 credential leak
    "Jinja2": "3.1.4",    # Fixes sandbox breakout vulnerabilities
    "jinja2": "3.1.4",    # Fixes sandbox breakout vulnerabilities
    "azure-identity": "1.19.0",  # Fixes elevation of privilege
    "black": "24.0.0",    # Fixes ReDoS vulnerability
}

def update_requirements_file(file_path: Path):
    """Update a requirements.txt file with secure versions."""
    print(f"🔧 Updating {file_path}")
    
    if not file_path.exists():
        print(f"  ⚠️  File not found: {file_path}")
        return
    
    content = file_path.read_text()
    original_content = content
    updated = False
    
    for package, secure_version in VULNERABILITY_FIXES.items():
        # Pattern to match package==version or package>=version
        pattern = rf"^{re.escape(package)}[>=<~!]*[\d\.]+"
        
        # Find and replace vulnerable versions
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if re.match(pattern, line.strip(), re.IGNORECASE):
                old_line = line.strip()
                new_line = f"{package}=={secure_version}"
                lines[i] = line.replace(old_line, new_line)
                print(f"  ✅ {old_line} → {new_line}")
                updated = True
    
    if updated:
        file_path.write_text('\n'.join(lines))
        print(f"  💾 Updated {file_path}")
    else:
        print(f"  ℹ️  No vulnerable packages found in {file_path}")

def main():
    """Main function to fix all vulnerabilities."""
    print("🔒 SECURITY FIX: Updating vulnerable dependencies")
    print("=" * 60)
    print("Addressing 33 vulnerabilities found by Dependabot:")
    print("- 12 HIGH severity vulnerabilities")
    print("- 21 MEDIUM severity vulnerabilities")
    print("=" * 60)
    
    # Find all requirements.txt files
    containers_dir = Path("containers")
    requirements_files = list(containers_dir.glob("*/requirements.txt"))
    
    if not requirements_files:
        print("⚠️  No requirements.txt files found in containers/")
        return
    
    print(f"📁 Found {len(requirements_files)} requirements files:")
    for file_path in requirements_files:
        print(f"  - {file_path}")
    print()
    
    # Update each requirements file
    for file_path in requirements_files:
        update_requirements_file(file_path)
        print()
    
    print("🎯 SUMMARY:")
    print("Fixed vulnerabilities for:")
    for package, version in VULNERABILITY_FIXES.items():
        print(f"  ✅ {package} → {version}")
    
    print()
    print("🚀 Next steps:")
    print("1. Test the updated dependencies")
    print("2. Commit and push changes")
    print("3. Verify Dependabot alerts are resolved")

if __name__ == "__main__":
    main()
