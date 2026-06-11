# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from pathlib import Path


def _get_project_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _get_prompt_dir() -> Path:
    return _get_project_root() / "config" / "AI"


def _load_prompt_file(filename: str) -> str:
    prompt_path = _get_prompt_dir() / filename

    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

    try:
        return prompt_path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise RuntimeError(f"Failed to read prompt file: {prompt_path}") from exc


ACTION_SYSTEM_PROMPT = _load_prompt_file("action.txt")
GENERATE_SYSTEM_PROMPT = _load_prompt_file("generate.txt")
AGENT_SYSTEM_PROMPT = _load_prompt_file("agent.md")
OPERATOR_SYSTEM_PROMPT = _load_prompt_file("operator.txt")
PAYLOAD_SYSTEM_PROMPT = _load_prompt_file("payload.txt")


__all__ = [
    "ACTION_SYSTEM_PROMPT",
    "GENERATE_SYSTEM_PROMPT",
    "AGENT_SYSTEM_PROMPT",
    "OPERATOR_SYSTEM_PROMPT",
    "PAYLOAD_SYSTEM_PROMPT",
]
