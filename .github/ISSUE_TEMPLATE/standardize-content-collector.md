---
name: Standardize content-collector storage-backed /collect flow
about: Task to finish the content-collector refactor, implement storage-backed collection, tests and CI gates
title: "Standardize content-collector: storage-backed /collect flow"
labels: enhancement, backend, needs-triage
assignees: ''
---

## Summary

Finish and harden the `content-collector` container so collections are saved to Azure Blob Storage (or Azurite for local dev) in a stable, versioned layout and covered by unit + integration tests.

## Goals

- Implement full storage-backed `/collect` flow that saves JSON to `raw-content/collections/YYYY/MM/DD/<collection_id>.json`.
- Ensure `BlobStorageClient` is used correctly (sync vs async) and that code paths work with Azurite locally and native Azure in CI.
- Add unit tests for service logic and a small integration test that verifies a saved blob in Azurite during local CI runs.
- Add CI coverage (pytest) to the ephemeral PR workflow and blocking gates on test failures.

## Acceptance criteria

- [ ] Endpoint `/collect` persists collections to blob storage in the agreed path format.
- [ ] Unit tests exist for `ContentCollectorService.collect_and_store_content`, covering dedup and metadata.
- [ ] Integration test validates that a saved collection blob can be read back (using Azurite in CI or mocked blob client).
- [ ] CI (PR ephemeral workflow) runs the container tests and fails on test failures.
- [ ] README or comments document how to run the tests locally and how to switch between Azurite and Azure.

## Files likely to change

- `containers/content-collector/service_logic.py`
- `containers/content-collector/main.py`
- `containers/content-collector/blob_storage.py`
- `containers/content-collector/models.py`
- `containers/content-collector/requirements.txt`
- `containers/content-collector/tests/` (new)

## Test plan

1. Add unit tests (pytest) for `collect_and_store_content` using temporary directories or mocked `BlobStorageClient`.
2. Add an integration test that runs `Azurite` (or uses a CI-provided emulator) and confirms a blob is created and contains a valid JSON with expected metadata.

## Notes / Deployment

- Use Azurite for local dev. CI and production must use native Azure Blob Storage.
- Keep API contract stable; include API versioning metadata in responses.

## Estimate

2-4 days of focused work (implementation + tests + CI tweaks) depending on test infra availability.
