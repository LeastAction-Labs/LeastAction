# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from github import Github, InputGitTreeElement
import sys

from src.common.secrets import get_secret

GITHUB_TOKEN = get_secret("SYNC_BOT_TOKEN")
CORE_REPO_NAME = "LeastAction-Labs/LeastAction"
LITE_REPO_NAME = "LeastAction-Labs/LeastAction-Lite-POC"
LITE_REPO_BASE_BRANCH = "main"


def tranform_file_contents(file_changes: dict[str, str]) -> dict[str, str]:
    transformed = {}
    for filename, content in file_changes.items():
        if filename.startswith("src/core/ee/"):
            continue
        if filename.startswith(".github"):
            if filename == ".github/workflows/sync_to_lite.yml":
                continue
            transformed[filename] = content
        if filename.endswith("")
        # 5 for py. yml and 7 for tsx and ts

    return transformed

def create_pr_from_commit(commit_sha):
    g = Github(GITHUB_TOKEN)

    # 1. Connect to Repo 1 and extract file changes
    print(f"Connecting to Source Repo: {CORE_REPO_NAME}...")
    repo_1 = g.get_repo(LITE_REPO_NAME)

    try:
        source_commit = repo_1.get_commit(commit_sha)
    except Exception as e:
        print(f"Error: Could not find commit {commit_sha} in {CORE_REPO_NAME}. {e}")
        return

    commit_msg = source_commit.commit.message
    print(f"Found commit: '{commit_msg}'")

    file_changes = {}
    for file in source_commit.files:
        # For now, capturing added/modified text files cleanly
        if file.status in ["modified", "added"]:
            try:
                content_file = repo_1.get_contents(file.filename, ref=commit_sha)
                file_changes[file.filename] = content_file.decoded_content.decode('utf-8')
                print(f"  -> Extracted: {file.filename}")
            except Exception as e:
                print(f"  -> Skipping binary file or errored file {file.filename}: {e}")

    if not file_changes:
        print("No valid text files found to transfer. Exiting.")
        return

    # 2. Connect to Repo 2
    print(f"\nConnecting to Destination Repo: {LITE_REPO_NAME}...")
    repo_2 = g.get_repo(LITE_REPO_NAME)

    # Get Repo 2's latest base branch state to fork from
    repo_2_main = repo_2.get_branch(LITE_REPO_BASE_BRANCH)
    repo_2_base_sha = repo_2_main.commit.sha

    # 3. Create a unique new branch in Repo 2
    new_branch_name = f"sync/commit-{commit_sha[:7]}"
    ref_path = f"refs/heads/{new_branch_name}"

    try:
        repo_2.create_git_ref(ref=ref_path, sha=repo_2_base_sha)
        print(f"Created new branch in Repo 2: {new_branch_name}")
    except Exception:
        print(f"Branch '{new_branch_name}' already exists in Repo 2. Proceeding to overwrite contents...")

    # 4. Build the Git Tree for a single batch commit
    print("Building commit tree elements...")
    tree_element_list = []
    for file_path, content in file_changes.items():
        element = InputGitTreeElement(
            path=file_path,
            mode='100644',
            type='blob',
            content=content
        )
        tree_element_list.append(element)

    repo_2_base_commit = repo_2.get_git_commit(repo_2_base_sha)
    repo_2_base_tree = repo_2_base_commit.tree

    # Generate tree and create commit
    new_tree = repo_2.create_git_tree(tree_element_list, repo_2_base_tree)
    sync_commit_msg = f"sync: carry over files from {CORE_REPO_NAME}@{commit_sha[:7]}\n\nOriginal message: {commit_msg}"

    new_commit = repo_2.create_git_commit(
        message=sync_commit_msg,
        tree=new_tree,
        parents=[repo_2_base_commit]
    )

    # Update branch pointer to our new commit
    ref = repo_2.get_git_ref(f"heads/{new_branch_name}")
    ref.edit(sha=new_commit.sha)
    print("Committed changes to the new branch successfully.")

    # 5. Open the Pull Request in Repo 2
    print("Opening Pull Request...")
    try:
        pr = repo_2.create_pull(
            title=f"Sync changes from {CORE_REPO_NAME} commit {commit_sha[:7]}",
            body=f"Automated PR syncing changes from copy-pasted commit layout.\n\n**Original Commit Message:**\n> {commit_msg}",
            head=new_branch_name,
            base=LITE_REPO_BASE_BRANCH
        )
        print(f"🎉 Success! Pull Request created: {pr.html_url}")
    except Exception as e:
        print(f"Failed to create PR (It might already exist): {e}")


if __name__ == "__main__":
    # You can pass the SHA as a command line argument: python script.py <SHA>
    if len(sys.argv) > 1:
        target_sha = sys.argv[1]
    else:
        # Fallback manual input if not provided in terminal command
        target_sha = input("Enter the Repo 1 commit SHA to sync: ").strip()

    if target_sha:
        create_pr_from_commit(target_sha)
    else:
        print("No SHA provided. Exiting.")
