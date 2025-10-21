"""Helper script for working with versions in CI."""

import argparse
import json
import re
import sys
from pathlib import Path

from git import InvalidGitRepositoryError, Repo


def get_current_branch(path="."):
    try:
        repo = Repo(path, search_parent_directories=True)
        return repo.active_branch.name
    except InvalidGitRepositoryError:
        return None


def validate_release_branch(branch_name, finalize=False):
    """
    Validate that the branch name follows the required pattern.

    The valid patterns are:
    - prepare-release-X.Y.Z for final releases
    - prepare-release-X.Y.Z-alpha.N for alpha releases
    - prepare-release-X.Y.Z-rc.N for release candidates

    Args:
        branch_name: The branch name to validate
        finalize: If True, return only X.Y.Z without prerelease suffix

    Returns:
        tuple: (is_valid, version_string) where version_string is the full or finalized version

    """
    prefix = "prepare-release-"
    if not branch_name.startswith(prefix):
        return False, None

    version = branch_name.removeprefix(prefix)

    # Check for prerelease suffix (alpha or rc)
    base_version = version
    for suffix_pattern in ["-alpha.", "-rc."]:
        if suffix_pattern in version:
            base_version, suffix_num = version.split(suffix_pattern, 1)

            # Validate suffix number is a non-negative integer
            try:
                num = int(suffix_num)
                if num < 0:
                    return False, None
            except ValueError:
                return False, None
            break

    # Validate base version format: must be X.Y.Z (three parts)
    parts = base_version.split(".")
    if len(parts) != 3:
        return False, None

    try:
        # All parts must be non-negative integers
        for part in parts:
            if int(part) < 0:
                return False, None
    except ValueError:
        return False, None

    # Return finalized version (X.Y.Z) or full version
    return True, base_version if finalize else version


def get_version_from_file(pyproject_path=Path("pyproject.toml")):
    """Read the current version from pyproject.toml and convert from PEP 440."""
    if not pyproject_path.exists():
        print(f"ERROR: {pyproject_path} not found.", file=sys.stderr)
        sys.exit(1)

    content = pyproject_path.read_text(encoding="utf-8")

    for line in content.splitlines():
        if line.startswith("version = "):
            version_match = re.search(r'version = "([^"]+)"', line)
            if version_match:
                pep440_version = version_match.group(1)
                # Convert PEP 440 back to our format
                # 0.1.0a1 -> 0.1.0-alpha.1
                # 0.1.0rc1 -> 0.1.0-rc.1
                version = pep440_version
                version = re.sub(r"a(\d+)", r"-alpha.\1", version)
                version = re.sub(r"rc(\d+)", r"-rc.\1", version)
                return version

    print(f"ERROR: Could not find version field in {pyproject_path}.", file=sys.stderr)
    sys.exit(1)


def parse_version(version_str):
    """
    Parse a version string into components.

    Examples:
        0.1.0 -> (0, 1, 0, None, None)
        0.1.0-alpha.1 -> (0, 1, 0, 'alpha', 1)
        0.1.0-rc.2 -> (0, 1, 0, 'rc', 2)

    Returns:
        tuple: (major, minor, patch, prerelease_id, prerelease_num) or None if invalid

    """
    pattern = r"^(\d+)\.(\d+)\.(\d+)(?:-(alpha|rc)\.(\d+))?$"
    match = re.match(pattern, version_str)

    if not match:
        return None

    major, minor, patch, pre_id, pre_num = match.groups()
    return (int(major), int(minor), int(patch), pre_id, int(pre_num) if pre_num else None)


def format_version(major, minor, patch, pre_id=None, pre_num=None):
    """Format version components into a version string."""
    version = f"{major}.{minor}.{patch}"
    if pre_id and pre_num is not None:
        version += f"-{pre_id}.{pre_num}"
    return version


def cmd_get_version(args):
    """Get version from git branch or file."""
    from_source = args.from_source if hasattr(args, "from_source") else "git"
    finalize = args.finalize if hasattr(args, "finalize") else False

    if from_source == "git":
        branch = get_current_branch()
        if not branch:
            print("ERROR: Not in a git repository.", file=sys.stderr)
            sys.exit(1)

        is_valid, version = validate_release_branch(branch, finalize=finalize)
        if not is_valid:
            print(f"ERROR: Branch name '{branch}' does not match required pattern.", file=sys.stderr)
            print("Expected pattern: prepare-release-X.Y.Z[-alpha.N|-rc.N]", file=sys.stderr)
            sys.exit(1)
    else:  # from file
        version = get_version_from_file()

        # If finalize is requested, strip prerelease info
        if finalize:
            parsed = parse_version(version)
            if parsed:
                major, minor, patch, _, _ = parsed
                version = format_version(major, minor, patch)

    # Convert to PEP 440 format
    # 0.x.y-alpha.N -> 0.x.yaN
    # 0.x.y-rc.N -> 0.x.yrcN
    pep440_version = version.replace("-alpha.", "a").replace("-rc.", "rc")

    print(f"Release version: {version}")
    print(f"PEP 440 version: {pep440_version}")


def update_pyproject_version(version: str, pyproject_path: Path = Path("pyproject.toml")):
    """Update the version in pyproject.toml."""
    if not pyproject_path.exists():
        print(f"ERROR: {pyproject_path} not found.", file=sys.stderr)
        sys.exit(1)

    content = pyproject_path.read_text(encoding="utf-8")
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

    pyproject_path.write_text("".join(lines), encoding="utf-8")
    print(f"  - Updated {pyproject_path} to version {version}")


def update_package_json_version(version: str, package_json_path: Path = Path("frontend/package.json")):
    """Update the version in frontend/package.json."""
    if not package_json_path.exists():
        print(f"ERROR: {package_json_path} not found.", file=sys.stderr)
        sys.exit(1)

    with package_json_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    data["version"] = version

    with package_json_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent="\t")
        f.write("\n")

    print(f"  - Updated {package_json_path} to version {version}")


def cmd_set_version(args):
    """Update the version in pyproject.toml and frontend/package.json."""
    version = args.version

    # Convert to PEP 440 format for pyproject.toml
    # 0.x.y-alpha.N -> 0.x.yaN
    # 0.x.y-rc.N -> 0.x.yrcN
    pep440_version = version.replace("-alpha.", "a").replace("-rc.", "rc")

    update_pyproject_version(pep440_version)
    update_package_json_version(version)

    print(f"Successfully updated pyproject.toml to {pep440_version} and package.json to {version}")


def cmd_version(args):
    """Bump version and update files."""
    # Get current version from file
    current_version = get_version_from_file()
    parsed = parse_version(current_version)

    if not parsed:
        print(f"ERROR: Invalid version format in file: {current_version}", file=sys.stderr)
        sys.exit(1)

    major, minor, patch, pre_id, pre_num = parsed

    if args.exact:
        # Set exact version
        new_version = args.exact
    elif args.bump == "prerelease":
        # Bump prerelease version
        if not args.pre_id:
            print("ERROR: --pre-id is required when bumping prerelease", file=sys.stderr)
            sys.exit(1)

        if pre_id == args.pre_id:
            # Same pre-id, just increment the number
            new_pre_num = (pre_num if pre_num is not None else 0) + 1
            new_version = format_version(major, minor, patch, args.pre_id, new_pre_num)
        else:
            # Different pre-id, start at 1
            new_version = format_version(major, minor, patch, args.pre_id, 1)
    else:
        print(f"ERROR: Unknown bump type: {args.bump}", file=sys.stderr)
        sys.exit(1)

    # Update files with new version
    pep440_version = new_version.replace("-alpha.", "a").replace("-rc.", "rc")
    update_pyproject_version(pep440_version)
    update_package_json_version(new_version)

    print(f"Bumped version from {current_version} to {new_version}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Version management utilities")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # get-version command
    get_version_parser = subparsers.add_parser(
        "get-version",
        help="Get version from git branch or file.",
    )
    get_version_parser.add_argument(
        "--from",
        dest="from_source",
        choices=["git", "file"],
        default="git",
        help="Source to get version from (default: git)",
    )
    get_version_parser.add_argument(
        "--finalize", action="store_true", help="Strip prerelease suffix and return only X.Y.Z"
    )
    get_version_parser.set_defaults(func=cmd_get_version)

    # set-version command
    set_version_parser = subparsers.add_parser(
        "set-version", help="Update the version in pyproject.toml and frontend/package.json"
    )
    set_version_parser.add_argument("version", help="The version string to set (e.g., 0.26.0 or 0.26.0-alpha.1)")
    set_version_parser.set_defaults(func=cmd_set_version)

    # version command
    version_parser = subparsers.add_parser("version", help="Bump version in files")
    version_group = version_parser.add_mutually_exclusive_group(required=True)
    version_group.add_argument("--exact", help="Set exact version (e.g., 0.1.0)")
    version_group.add_argument("--bump", choices=["prerelease"], help="Bump type")
    version_parser.add_argument(
        "--pre-id", choices=["alpha", "rc"], help="Prerelease identifier (required with --bump prerelease)"
    )
    version_parser.set_defaults(func=cmd_version)

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
