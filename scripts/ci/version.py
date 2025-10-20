from git import Repo, InvalidGitRepositoryError

def get_current_branch(path="."):
    try:
        repo = Repo(path, search_parent_directories=True)
        return repo.active_branch.name
    except InvalidGitRepositoryError:
        return None

if __name__ == "__main__":
    branch = get_current_branch()
    if branch:
        print(f"Current branch: {branch}")
    else:
        print("Not in a git repository.")
