# Releases and versioning

This document describes the current release and versioning strategy.

## Release cadence

New releases of the Rerun Gradio integration are published alongside Rerun releases, typically once per month.

## Library versioning

The project follows semantic versioning with versions synchronized to Rerun releases (e.g. `0.22.0`, `0.23.0`, ...).

This means we might add breaking changes in each new release.

# Release process

The release process is automated via GitHub Actions. Follow these steps:

## 1. Create a release branch

Create a new branch from `main` with a name following the pattern:

- `prepare-release-X.Y.Z` for final releases and their release candidates
- `prepare-release-X.Y.Z-alpha.N` for alpha releases (where `N` starts at 1)

Examples:

- `prepare-release-0.26.0` - for version 0.26.0 (used for both RC and final releases).
- `prepare-release-0.26.0-alpha.1` - for alpha version 0.26.0-alpha.1

**Important:** Always specify all three version numbers (X.Y.Z), even if the last number is 0.
For example, use `prepare-release-0.26.0` not `prepare-release-0.26`.

```sh
# Example: creating a release branch for 0.26.0
git checkout main
git pull
git checkout -b prepare-release-0.26.0
git push -u origin prepare-release-0.26.0
```

## 2. Trigger the release workflow

Navigate to the [Release workflow](https://github.com/rerun-io/gradio-rerun-viewer/actions/workflows/release.yml) in GitHub Actions and click "Run workflow".

Select the release type:

- **alpha**: For early testing releases (e.g., `0.26.0-alpha.1`, `0.26.0-alpha.2`, ...)
- **rc**: For release candidates (e.g., `0.26.0-rc.1`, `0.26.0-rc.2`, ...)
- **final**: For the final release (e.g., `0.26.0`)

The workflow will automatically:

1. Determine the target version from the branch name
2. Bump the version appropriately based on the release type
3. Update Rerun dependencies (`rerun-sdk` and `@rerun-io/web-viewer`)
4. Update package versions in `pyproject.toml` and `frontend/package.json`
5. Run linting and formatting checks
6. Build and publish the Gradio component to PyPI and npm
7. Create a draft GitHub release (for RC and final releases)

## 3. Verify the release

After the workflow completes:

1. Check that the version was bumped correctly in the commit history
2. Verify the package was published to PyPI: <https://pypi.org/project/gradio-rerun-viewer/>
3. For RC and final releases, review and publish the draft GitHub release

## 4. Update the example space on Huggingface

Gradio does not currently have an option to pick a specific repo id when publishing, so the space has to be updated manually (gradio-app/gradio#11240).

1. Check out [the Huggingface space](https://huggingface.co/spaces/rerun/gradio-rerun-viewer) using git:

    ```sh
    git clone git@hf.co:spaces/rerun/gradio-rerun-viewer
    ```

2. Update the package version in the `requirements.txt`.
3. Commit and push the changes.

## Version numbering

- **Alpha releases**: Start at `.1` and increment (e.g., `0.26.0-alpha.1`, `0.26.0-alpha.2`)
- **Release candidates**: Start at `.1` and increment (e.g., `0.26.0-rc.1`, `0.26.0-rc.2`)
- **Final releases**: No suffix (e.g., `0.26.0`)
