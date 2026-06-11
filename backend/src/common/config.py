# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from pathlib import Path
from typing import Any

import yaml


class Config:
    """Application configuration loader."""

    def __init__(self, config_path: str | None = None):
        root_path = None
        current_path = Path(__file__).resolve()
        for file_path in [current_path] + list(current_path.parents):
            if file_path.name == "backend":
                root_path = file_path.parent
                break
        if not root_path:
            raise
        self.root_path = root_path
        default_config_path = self.root_path / "config" / "system.yml"
        self.config_path = Path(config_path) if config_path else default_config_path
        self._config_data: dict[str, Any] | None = None

    def _load_config(self) -> dict[str, Any] | None:
        """Load configuration from YAML file."""
        if self._config_data is None:
            if not self.config_path.exists():
                raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

            with self.config_path.open("r", encoding="utf-8") as f:
                self._config_data = yaml.safe_load(f)

        return self._config_data

    @property
    def logs_dir(self) -> Path:
        config = self._load_config()
        if config is None:
            raise ValueError("Configuration data is empty or invalid.")
        logs_config = config.get("logs")
        if not logs_config or "directory" not in logs_config:
            raise KeyError("Missing 'logs.directory' in configuration file.")

        logs_dir = Path(logs_config["directory"])
        if not logs_dir.is_absolute():
            logs_dir = self.root_path / logs_dir
        logs_dir.mkdir(parents=True, exist_ok=True)

        return logs_dir
