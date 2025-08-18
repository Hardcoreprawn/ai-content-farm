---
name: Ephemeral PR environment for Container Apps + Infracost
about: Provision ephemeral environments per PR (Terraform workspace + Container Apps + Key Vault + Storage) and wire Infracost and security scans
title: "Add ephemeral PR environment: container apps + infra + cost checks"
labels: infra, terraform, needs-triage
assignees: ''
---

## Summary

Implement and harden ephemeral PR environments that provision a resource group / terraform workspace per PR, deploy necessary infra (Container Apps or Container Instances, Storage, Key Vault, Log Analytics), run security scans and Infracost, and tear down on PR close.

## Goals

- Create terraform modules (or reuse `infra/` patterns) to provision a small environment for each PR.
- Ensure `terraform workspace` naming uses `pr-<pr-number>` and that GitHub workflow destroys the workspace on PR close.
- Add Infracost config and posting to PR comments.
- Add quick security scans (Trivy/Checkov) to the ephemeral workflow.

## Acceptance criteria

- [ ] Terraform prototype for ephemeral environments added under `infra/` and referenced by `.github/workflows/ephemeral-environment.yml`.
- [ ] Workflow creates workspace per PR and destroys it on close (already present; validate and harden).
- [ ] Infracost runs and comments on PR with cost estimate.
- [ ] Integration tests run against the ephemeral environment and are green.

## Files likely to change

- `infra/` (new or modified modules)
- `.github/workflows/ephemeral-environment.yml` (validate and harden)
- `containers/*` (adjust container builds and health endpoints for smoke tests)

## Estimate

3-6 days depending on existing infra modules and ACR/Container Apps implementation.
