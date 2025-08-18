## Summary

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
