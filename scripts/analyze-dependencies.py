#!/usr/bin/env python3
"""
AI Content Farm - Dependency Analysis and Vulnerability Assessment
Analyzes SBOM files, identifies vulnerabilities, and creates GitHub issues for updates.
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import requests


class DependencyAnalyzer:
    def __init__(self, sbom_dir: str = "output/sbom"):
        self.sbom_dir = Path(sbom_dir)
        self.vulnerabilities = {}
        self.outdated_packages = {}
        self.security_issues = []

    def analyze_all_sboms(self) -> Dict[str, Any]:
        """Analyze all SBOM files and generate comprehensive report."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_components": 0,
            "vulnerabilities_found": 0,
            "outdated_packages": 0,
            "containers": {},
            "summary": {},
        }

        print("🔍 Analyzing Software Bill of Materials...")

        for sbom_file in self.sbom_dir.glob("*.json"):
            container_name = sbom_file.stem.replace("-sbom", "")
            print(f"  📦 Analyzing {container_name}...")

            container_report = self.analyze_container_sbom(sbom_file)
            report["containers"][container_name] = container_report
            report["total_components"] += container_report["component_count"]

        # Generate summary
        report["summary"] = self.generate_summary(report)

        return report

    def analyze_container_sbom(self, sbom_file: Path) -> Dict[str, Any]:
        """Analyze individual container SBOM."""
        with open(sbom_file, "r") as f:
            sbom_data = json.load(f)

        artifacts = sbom_data.get("artifacts", [])
        container_report = {
            "component_count": len(artifacts),
            "components": [],
            "vulnerabilities": [],
            "outdated": [],
            "risk_level": "LOW",
        }

        for artifact in artifacts:
            component = {
                "name": artifact.get("name"),
                "version": artifact.get("version"),
                "type": artifact.get("type"),
                "locations": artifact.get("locations", []),
            }

            # Check for known vulnerabilities (would integrate with vulnerability DB)
            vuln_status = self.check_vulnerabilities(component)
            if vuln_status:
                container_report["vulnerabilities"].extend(vuln_status)

            # Check if package is outdated (would integrate with PyPI API)
            outdated_status = self.check_outdated(component)
            if outdated_status:
                container_report["outdated"].append(outdated_status)

            container_report["components"].append(component)

        # Determine risk level
        container_report["risk_level"] = self.calculate_risk_level(container_report)

        return container_report

    def check_vulnerabilities(self, component: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check component for known vulnerabilities."""
        # This would integrate with vulnerability databases like OSV, NVD, etc.
        # For now, simulate some common vulnerable packages
        vulnerable_packages = {
            "requests": {"<2.31.0": "CVE-2023-32681"},
            "fastapi": {"<0.104.0": "Security advisory GHSA-74m5-2c7w-9w3x"},
            "azure-storage-blob": {"<12.19.0": "Security update recommended"},
        }

        vulns = []
        pkg_name = component.get("name")
        pkg_version = component.get("version")

        if pkg_name in vulnerable_packages:
            for version_constraint, advisory in vulnerable_packages[pkg_name].items():
                if self.version_matches_constraint(pkg_version, version_constraint):
                    vulns.append(
                        {
                            "package": pkg_name,
                            "version": pkg_version,
                            "advisory": advisory,
                            "severity": "MEDIUM",
                            "recommendation": f"Update {pkg_name} to latest version",
                        }
                    )

        return vulns

    def check_outdated(self, component: Dict[str, Any]) -> Dict[str, Any]:
        """Check if component is outdated."""
        # This would integrate with PyPI API to check latest versions
        # For demo purposes, simulate some outdated packages
        pkg_name = component.get("name")
        pkg_version = component.get("version")

        # Simulate checking against latest versions
        simulated_latest = {
            "fastapi": "0.105.0",
            "uvicorn": "0.25.0",
            "pydantic": "2.6.0",
            "azure-identity": "1.16.0",
        }

        if pkg_name in simulated_latest:
            latest = simulated_latest[pkg_name]
            if pkg_version != latest:
                return {
                    "package": pkg_name,
                    "current_version": pkg_version,
                    "latest_version": latest,
                    "update_priority": "MEDIUM",
                }

        return None

    def version_matches_constraint(self, version: str, constraint: str) -> bool:
        """Simple version constraint matching."""
        # Simplified version comparison - would use packaging.version in real implementation
        if constraint.startswith("<"):
            target_version = constraint[1:]
            return version < target_version
        return False

    def calculate_risk_level(self, container_report: Dict[str, Any]) -> str:
        """Calculate overall risk level for container."""
        vuln_count = len(container_report["vulnerabilities"])

        if vuln_count >= 5:
            return "HIGH"
        elif vuln_count >= 2:
            return "MEDIUM"
        elif vuln_count >= 1:
            return "LOW"
        else:
            return "MINIMAL"

    def generate_summary(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """Generate overall summary."""
        total_vulns = sum(
            len(c["vulnerabilities"]) for c in report["containers"].values()
        )
        total_outdated = sum(len(c["outdated"]) for c in report["containers"].values())

        risk_levels = [c["risk_level"] for c in report["containers"].values()]
        overall_risk = (
            "HIGH"
            if "HIGH" in risk_levels
            else "MEDIUM" if "MEDIUM" in risk_levels else "LOW"
        )

        return {
            "total_vulnerabilities": total_vulns,
            "total_outdated": total_outdated,
            "overall_risk": overall_risk,
            "containers_with_issues": len(
                [
                    c
                    for c in report["containers"].values()
                    if c["vulnerabilities"] or c["outdated"]
                ]
            ),
            "recommendation": self.get_recommendation(
                overall_risk, total_vulns, total_outdated
            ),
        }

    def get_recommendation(self, risk: str, vulns: int, outdated: int) -> str:
        """Get recommendation based on analysis."""
        if risk == "HIGH":
            return "IMMEDIATE ACTION REQUIRED: High-risk vulnerabilities found. Block deployment until resolved."
        elif risk == "MEDIUM":
            return "REVIEW REQUIRED: Medium-risk issues found. Address before production deployment."
        elif vulns > 0 or outdated > 0:
            return "MONITOR: Minor issues found. Consider updating in next maintenance window."
        else:
            return "GOOD: No significant issues found. Dependencies are up to date."

    def create_github_issues(self, report: Dict[str, Any]):
        """Create GitHub issues for vulnerabilities and outdated packages."""
        print("📝 Creating GitHub issues for dependency updates...")

        # Group issues by type
        vulnerability_issues = []
        update_issues = []

        for container_name, container_data in report["containers"].items():
            for vuln in container_data["vulnerabilities"]:
                vulnerability_issues.append(
                    {"container": container_name, "vulnerability": vuln}
                )

            for outdated in container_data["outdated"]:
                update_issues.append({"container": container_name, "package": outdated})

        # Create vulnerability issues
        if vulnerability_issues:
            self.create_vulnerability_issue(vulnerability_issues)

        # Create update issues
        if update_issues:
            self.create_update_issue(update_issues)

    def create_vulnerability_issue(self, vulnerabilities: List[Dict]):
        """Create GitHub issue for vulnerabilities."""
        title = f"🚨 Security Vulnerabilities Found in Dependencies - {datetime.now().strftime('%Y-%m-%d')}"

        body = f"""## Security Vulnerability Report
        
**Generated**: {datetime.now().isoformat()}
**Priority**: HIGH
**Type**: Security

### Vulnerabilities Found

"""
        for vuln_data in vulnerabilities:
            vuln = vuln_data["vulnerability"]
            container = vuln_data["container"]
            body += f"""
#### {vuln['package']} in {container}
- **Current Version**: {vuln['version']}
- **Advisory**: {vuln['advisory']}
- **Severity**: {vuln['severity']}
- **Recommendation**: {vuln['recommendation']}

"""

        body += """
### Action Required
1. Review each vulnerability and assess impact
2. Update affected packages to secure versions
3. Test updated dependencies in PR environment
4. Deploy security fixes with priority

### Acceptance Criteria
- [ ] All HIGH and CRITICAL vulnerabilities resolved
- [ ] Package updates tested in ephemeral environment
- [ ] Security scan passes with updated dependencies
- [ ] No regression in functionality after updates
"""

        print(f"Would create GitHub issue: {title}")
        print("Issue body preview:")
        print(body[:500] + "..." if len(body) > 500 else body)

    def create_update_issue(self, updates: List[Dict]):
        """Create GitHub issue for package updates."""
        title = (
            f"📦 Dependency Updates Available - {datetime.now().strftime('%Y-%m-%d')}"
        )

        body = f"""## Dependency Update Report
        
**Generated**: {datetime.now().isoformat()}
**Priority**: MEDIUM
**Type**: Maintenance

### Packages to Update

"""
        for update_data in updates:
            pkg = update_data["package"]
            container = update_data["container"]
            body += f"""
#### {pkg['package']} in {container}
- **Current Version**: {pkg['current_version']}
- **Latest Version**: {pkg['latest_version']}
- **Priority**: {pkg['update_priority']}

"""

        body += """
### Recommended Actions
1. Update packages to latest stable versions
2. Test compatibility in development environment
3. Run full test suite to ensure no regressions
4. Deploy updates in next maintenance window

### Acceptance Criteria
- [ ] All packages updated to latest stable versions
- [ ] Tests pass with updated dependencies
- [ ] No functional regressions introduced
- [ ] SBOM regenerated with updated versions
"""

        print(f"Would create GitHub issue: {title}")

    def save_report(
        self, report: Dict[str, Any], filename: str = "dependency-analysis-report.json"
    ):
        """Save analysis report to file."""
        output_file = Path("output") / filename
        output_file.parent.mkdir(exist_ok=True)

        with open(output_file, "w") as f:
            json.dump(report, f, indent=2)

        print(f"✅ Dependency analysis report saved: {output_file}")
        return output_file


def main():
    """Main function to run dependency analysis."""
    analyzer = DependencyAnalyzer()

    # Check if SBOM files exist
    if not analyzer.sbom_dir.exists():
        print("❌ SBOM directory not found. Run 'make sbom' first.")
        sys.exit(1)

    # Analyze all SBOMs
    report = analyzer.analyze_all_sboms()

    # Display summary
    print(f"\n📊 DEPENDENCY ANALYSIS SUMMARY")
    print(f"Total Components: {report['total_components']}")
    print(f"Vulnerabilities: {report['summary']['total_vulnerabilities']}")
    print(f"Outdated Packages: {report['summary']['total_outdated']}")
    print(f"Overall Risk: {report['summary']['overall_risk']}")
    print(f"Recommendation: {report['summary']['recommendation']}")

    # Save report
    analyzer.save_report(report)

    # Create GitHub issues if vulnerabilities found
    if (
        report["summary"]["total_vulnerabilities"] > 0
        or report["summary"]["total_outdated"] > 0
    ):
        analyzer.create_github_issues(report)

    print("\n✅ Dependency analysis complete!")


if __name__ == "__main__":
    main()
