"""Helper script for working with versions in CI."""

import argparse
import json
import sys
from pathlib import Path

from git import InvalidGitRepositoryError, Repo


def get_current_branch(path="."):
    try:
        repo = Repo(path, search_parent_directories=True)
        return repo.active_branch.name
    except InvalidGitRepositoryError:
        return None


def validate_release_branch(branch_name):
    """
    Validate that the branch name follows the required pattern.

    The valid patterns are:
    - prepare-release-0.x.y for minor and patch releases
    - prepare-release-0.x.y-alpha.N for alpha releases.

    Returns:
        tuple: (is_valid, version_string) where version_string is the full version if valid

    """
    prefix = "prepare-release-"
    if not branch_name.startswith(prefix):
        return False, None

    version = branch_name.removeprefix(prefix)

    # Check for alpha suffix
    is_alpha = "-alpha." in version
    if is_alpha:
        # Split on -alpha. to get base version and alpha number
        base_version, alpha_suffix = version.split("-alpha.", 1)

        # Validate alpha number is a positive integer
        try:
            alpha_num = int(alpha_suffix)
            if alpha_num < 0:
                return False, None
        except ValueError:
            return False, None

        version_to_check = base_version
    else:
        version_to_check = version

    # Validate base version format: must be 0.x.y (three parts, first part is 0)
    parts = version_to_check.split(".")
    if len(parts) != 3:
        return False, None

    try:
        # Second and third parts must be non-negative integers
        int(parts[1])
        int(parts[2])
    except ValueError:
        return False, None

    return True, version


def cmd_get_version(_args):
    """Validate that the current branch follows the prepare-release-X.Y.Z pattern."""
    branch = get_current_branch()
    if not branch:
        print("ERROR: Not in a git repository.", file=sys.stderr)
        sys.exit(1)

    is_valid, version = validate_release_branch(branch)
    if not is_valid:
        print(f"ERROR: Branch name '{branch}' does not match required pattern.", file=sys.stderr)
        print("Expected pattern: prepare-release-X.Y.Z (e.g., prepare-release-1.2.3)", file=sys.stderr)
        sys.exit(1)

    print(f"Release version: {version}")


def update_pyproject_version(version: str, pyproject_path: Path = Path("pyproject.toml")):
    """Update the version in pyproject.toml."""
    if not pyproject_path.exists():
        print(f"ERROR: {pyproject_path} not found.", file=sys.stderr)
        sys.exit(1)

    content = pyproject_path.read_text()
    lines = content.splitlines(keepends=True)

    updated = False
    for i, line in enumerate(lines):
        if line.startswith("version = "):
            lines[i] = f'version = "{version}"\n'
            updated = True
            break

    if not updated:
        print(f"ERROR: Could not find version field in {pyproject_path}.", file=sys.stderr)
        sys.exit(1)

    pyproject_path.write_text("".join(lines))
    print(f"  - Updated {pyproject_path} to version {version}")


def update_package_json_version(version: str, package_json_path: Path = Path("frontend/package.json")):
    """Update the version in frontend/package.json."""
    if not package_json_path.exists():
        print(f"ERROR: {package_json_path} not found.", file=sys.stderr)
        sys.exit(1)

    with package_json_path.open("r") as f:
        data = json.load(f)

    data["version"] = version

    with package_json_path.open("w") as f:
        json.dump(data, f, indent="\t")
        f.write("\n")

    print(f"  - Updated {package_json_path} to version {version}")


def cmd_set_version(args):
    """Update the version in pyproject.toml and frontend/package.json."""
    version = args.version

    update_pyproject_version(version)
    update_package_json_version(version)

    print(f"Successfully updated version to {version} in both files")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Version management utilities")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    get_version_parser = subparsers.add_parser(
        "get-version",
        help="Validate that the current branch follows the prepare-release-X.Y.Z pattern, and print the version.",
    )
    get_version_parser.set_defaults(func=cmd_get_version)

    set_version_parser = subparsers.add_parser(
        "set-version", help="Update the version in pyproject.toml and frontend/package.json"
    )
    set_version_parser.add_argument("version", help="The version string to set (e.g., 0.26.0 or 0.26.0-alpha.1)")
    set_version_parser.set_defaults(func=cmd_set_version)

    args = parser.parse_args()

    if hasattr(args, "func"):
        args.func(args)
    else:
        # Default behavior when no subcommand is provided
        branch = get_current_branch()
        if branch:
            print(f"Current branch: {branch}")
        else:
            print("Not in a git repository.")
