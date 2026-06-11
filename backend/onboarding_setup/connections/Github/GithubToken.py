# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
connection_type = "git"

connection =  {
        "git_username": "your_github_username",
        "git_token": "ghp_xxxxxxxxxxxxxxxxxxxx"
}

prompt = "Configure GitHub Personal Access Token connection for Git-based actions like LeastActionGitToTask."

install_docs = """# GithubToken — Connection Setup

1. Go to GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Create a token with repo (read) access
3. Enter your username and the generated token below
"""

guide_docs = """# GithubToken — Connection Guide

Simple GitHub authentication connection used by LeastActionGitToTask and similar actions
that need to clone or pull from private GitHub repositories.
"""

description = "GitHub Personal Access Token connection for private repository access."

publisher = "LeastAction"

metadata = {
    "service": "GitHub",
    "category": "DevOps",
    "tags": ["github", "git", "token", "connection", "authentication"]
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}
