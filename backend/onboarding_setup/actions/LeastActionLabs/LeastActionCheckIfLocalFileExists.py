# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
bashblock = {'install_dependencies.sh': 'pip install pathlib'}

codeblock = {'main.py': 'import os\n'
                               'from pathlib import Path\n'
                               'from src.common.logger.logger import log_info, log_error\n'
                               '\n'
                               '\n'
                               'def run(least_action_action_object, file_path, **kwargs):\n'
                               '    """\n'
                               '    Check if a local file exists at the specified path.\n'
                               '    \n'
                               '    Parameters:\n'
                               '        least_action_action_object (dict): Action object '
                               'containing metadata\n'
                               '        file_path (str): Path to the file to check\n'
                               '    \n'
                               '    Returns:\n'
                               '        bool: True if file exists, False otherwise\n'
                               '    """\n'
                               '    try:\n'
                               '        log_info("action", "run", "start", f"Starting file '
                               'existence check for: {file_path}")\n'
                               '        \n'
                               '        if not file_path:\n'
                               '            log_error("action", "run", "validate_input", "File '
                               'path is empty or None")\n'
                               '            return False\n'
                               '        \n'
                               '        log_info("action", "run", "validate_input", f"Validating '
                               'file path: {file_path}")\n'
                               '        \n'
                               '        file_path_obj = Path(file_path)\n'
                               '        \n'
                               '        log_info("action", "run", "check_existence", f"Checking if '
                               'file exists at: {file_path_obj.absolute()}")\n'
                               '        \n'
                               '        if file_path_obj.exists():\n'
                               '            if file_path_obj.is_file():\n'
                               '                file_size = file_path_obj.stat().st_size\n'
                               '                log_info("action", "run", "file_found", f"File '
                               'exists. Size: {file_size} bytes")\n'
                               '                return True\n'
                               '            else:\n'
                               '                log_error("action", "run", "not_a_file", f"Path '
                               'exists but is not a file: {file_path}")\n'
                               '                return False\n'
                               '        else:\n'
                               '            log_error("action", "run", "file_not_found", f"File '
                               'does not exist: {file_path}")\n'
                               '            return False\n'
                               '    \n'
                               '    except PermissionError as e:\n'
                               '        log_error("action", "run", "permission_error", '
                               'f"Permission denied accessing file: {str(e)}")\n'
                               '        return False\n'
                               '    except OSError as e:\n'
                               '        log_error("action", "run", "os_error", f"OS error while '
                               'checking file: {str(e)}")\n'
                               '        return False\n'
                               '    except Exception as e:\n'
                               '        log_error("action", "run", "unexpected_error", '
                               'f"Unexpected error: {str(e)}")\n'
                               '        return False'}

action_variables = {'file_path': '/path/to/file.txt'}

prompt = (
    "Check whether a local file exists on the execution host filesystem. "
    "Action variable: file_path (absolute path to the file). "
    "Returns True if the file exists and is accessible, False otherwise. "
    "Handles PermissionError and OSError gracefully."
)

install_docs = """# LeastActionCheckIfLocalFileExists — Install Guide

## Dependencies

Uses Python standard library only (pathlib, os). No additional packages needed.
"""

guide_docs = """# LeastActionCheckIfLocalFileExists — Action Guide

## What it does

Checks whether a file exists at the given path on the executor's local filesystem.
Useful as a gate in workflows that depend on files being present before downstream tasks run.

---

## Action Variables

    {"file_path": "/data/output/results.csv"}

---

## Returns

True if the file exists. False if not found, permission denied, or any OS error.
"""

description = """
Checks whether a file exists at the given local path on the execution host.
Returns True if accessible, False on any error including permission denied or path not found.
"""

publisher = "LeastAction"

metadata = {
    "service": "LeastAction",
    "category": "Utility",
    "tags": ["file", "exists", "local", "check", "filesystem"],
    "airflow_equivalent": "FileSensor"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}
