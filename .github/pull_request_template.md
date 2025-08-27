## 🛑 STOP - Portfolio Project Notice

**This repository is a personal portfolio project and does not accept external contributions.**

### If you are:
- 🤖 **Dependabot**: Continue with your automated security updates!
- 🔒 **GitHub Security**: Continue with automated patches!
- 👤 **External contributor**: Thank you for your interest, but this repo doesn't accept external PRs

### 📋 Portfolio Project Information
This project demonstrates:
- AI-powered content generation
- Cloud-native architecture (Azure)
- Advanced CI/CD practices
- Enterprise security patterns

### 💡 Alternative Actions
Instead of a PR, you could:
- ⭐ **Star** the repository if you find it interesting
- 🐛 **Open an issue** to report bugs
- 💬 **Ask questions** about the architecture
- 🍴 **Fork** to create your own version

---

**If this is an automated security update, you may proceed.** 
**If this is a human contribution, please close this PR and consider the alternatives above.**

Thank you for understanding! 🚀

---

## Summary (for automated PRs)

Provide a short description of the change and the motivation.

## Linked issues

- Closes: # (link related issue)

## Changes

- What changed (files, modules)
- Why (design rationale)

## Checklist (required)

- [ ] I updated or added tests (pytest)
- [ ] Linting passes (black/isort/ruff)
- [ ] Security scans pass or findings are documented (Trivy/Checkov)
- [ ] Infracost cost estimate added to PR comments (if infra changes)
- [ ] Ephemeral environment: validated (if PR touches infra)
- [ ] API contract version bumped if there are breaking changes

## How to test locally

1. Run unit tests for changed containers:

```bash
cd containers/content-collector
python -m pytest -v
```

2. (Optional) Spin up Azurite for testing blob storage locally.

## Notes

Any special notes for reviewers, rollout plan, or migration steps.
