---
description: How to release a new version of fastapi-otp-auth
---

# Release Process

This workflow describes the steps to release a new version of `fastapi-otp-auth`.

## Prerequisites

- Ensure you have `uv` installed.
- Ensure you have Docker installed (for verification).

## Steps

1.  **Bump Version**:
    - Update the `version` in `pyproject.toml`.
    - Run `docker run --rm -v "$(pwd):/app" -w /app ghcr.io/astral-sh/uv:python3.13-bookworm-slim uv lock` to update `uv.lock`.

2.  **Verify**:
    - Run `make test` to ensure all tests pass.
    - Run `docker-compose -f docker-compose.test.yml run --rm app-test uv run ruff check .` to ensure linting passes.

3.  **Commit**:
    - Commit the changes: `git commit -am "Bump version to X.Y.Z"`
    - Push to `main`.

4.  **Release**:
    - Create a new GitHub Release with the tag `vX.Y.Z`.
    - This will trigger the `.github/workflows/publish.yml` workflow, which will build and publish the package to PyPI using `uv`.