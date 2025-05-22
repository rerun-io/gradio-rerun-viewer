# Releases and versioning

This document describes the current release and versioning strategy.

## Release cadence

New releases of the Rerun Gradio integration are published alongside Rerun releases, typically once per month.

## Library versioning

The project follows semantic versioning with versions synchronized to Rerun releases (e.g. `0.22.0`, `0.23.0`, ...).

This means we might add breaking changes in each new release.

# Release process

1. Check the root `pyproject.toml` to see what version of Rerun we are currently on.
2. Create a release branch.

    The name should be:

    - `release-0.x.y` for final releases and their release candidates.
    - `release-0.x.y-alpha.N` where `N` is incremented from the previous alpha, or defaulted to `1` if no previous alpha exists.

    > Note that `release-0.x` is invalid. Always specify the `y`, even if it is `0`, e.g. `release-0.15.0` instead of `release-0.15.`

3. Increment Rerun version and package version.

    Update the Rerun version in the following files:

    - `rerun-sdk` in `pyproject.toml`.
    - `@rerun-io/web-viewer` in `frontend/package.json`.

    Ensure both versions match exactly, then set the library version (in `pyproject.toml`) to the same value.

4. Build the Gradio component to update the docs and example

    Run `gradio cc build` to build the package and ensure there are no errors. This will generate updated documentation and example code in `demo/space.py`.

5. Publish the Gradio component

    Publish the Gradio component and PyPI package using the following command:

    ```sh
    gradio cc publish --upload-pypi --no-upload-demo --no-upload-source
    ```

    When prompted for PyPI credentials log in using a token ([token setup guide](https://pypi.org/help/#apitoken)).

6. Update the example space on Huggingface

    Gradio does not currently have an option to pick a specific repo id when publishing, so the space has to be updated manually (gradio-app/gradio#11240).

    1. Check out [the Huggingface space](https://huggingface.co/spaces/rerun/gradio-rerun-viewer) using git:

        ```sh
        git clone git@hf.co:spaces/rerun/gradio-rerun-viewer
        ```

    2. Update the package version in the `requirements.txt`.
    3. Commit and push the changes.
