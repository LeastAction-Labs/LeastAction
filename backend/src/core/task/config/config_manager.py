# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from datetime import UTC, datetime
from typing import Any

from jinja2 import Environment, Undefined

from src.common.logger.logger import log_error, log_warning
from src.core.task.schema import TaskValidationModel


class KeepUndefined(Undefined):
    def __str__(self):
        return "{{ " + self._undefined_name + " }}"

    def __repr__(self):
        return "{{ " + self._undefined_name + " }}"


class ConfigManager:
    def __init__(self):
        self.overridden_params: list[str] = []
        self.overridable_params: list[str] = []
        self.not_overridable_params: list[str] = []

    def cleanup(self):
        self.overridable_params = []
        self.not_overridable_params = []
        self.overridden_params = []

    # TODO system config merge
    # TODO runtime params

    def merge_configs(
        self,
        task_config: dict[str, Any],
        configs_data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Input Args:
        1. task_config
        2. configs_data , which contains task_configs and workflow_configs

        return merged configs of task_config , task_configs ,workflow_configs
        """

        task_configs = configs_data.get("task_configs", [])
        workflow_configs = configs_data.get("workflow_configs", [])

        configs_array = [workflow_configs, task_configs, [task_config]]

        merged = {}
        merged_value_sources = {}

        for configs in configs_array:
            overridden_keys_dict = {"root": []}

            for config in configs:
                # the attached task config wont be having a laui field
                source_laui = config.get("laui", "attached_task_config")

                # If config has "content" key (from DB), use it; otherwise use config directly (for task.config dict)
                source = config.get("content") if "content" in config else config

                self._merge_content(
                    target=merged,
                    target_value_sources=merged_value_sources,
                    source=source,
                    source_laui=source_laui,
                    overridden_keys_dict=overridden_keys_dict,
                    root=True,
                )

            self.overridable_params = merged.get("overridable", [])
            self.not_overridable_params = merged.get("not_overridable", [])
            self.overridden_params = []

        self.cleanup()

        return {"merged_config": merged, "merged_value_sources": merged_value_sources}

    def _merge_parameters(
        self,
        target: dict[str, any],
        target_value_sources: dict[str, any],
        source: dict[str, any],
        source_laui: str,
    ):
        # Ensure target has a parameters dict to merge into
        if not isinstance(target.get("parameters"), dict):
            target["parameters"] = {}
            target_value_sources["parameters"] = {}

        for parameter_key, parameter_value in source.items():
            if parameter_key in self.overridden_params:
                log_warning(
                    "api",
                    "ConfigManager",
                    "_merge_parameters",
                    f"Parameter '{parameter_key}' ignored - overridden by previous config",
                )
            elif (
                parameter_key not in self.not_overridable_params
                or parameter_key in self.overridable_params
            ):
                target["parameters"][parameter_key] = parameter_value
                target_value_sources["parameters"][parameter_key] = source_laui
                self.overridden_params.append(parameter_key)
            else:
                log_warning(
                    "api",
                    "ConfigManager",
                    "_merge_parameters",
                    f"Parameter '{parameter_key}' ignored - not overridable",
                )

    def _merge_content(
        self,
        target: dict[str, any],
        target_value_sources: dict[str, any],
        source: dict[str, any],
        source_laui: str,
        overridden_keys_dict: dict[str, any],
        root: bool = False,
    ):

        for key, value in source.items():
            if key == "parameters" and isinstance(value, dict) and root:
                self._merge_parameters(
                    target=target,
                    target_value_sources=target_value_sources,
                    source=value,
                    source_laui=source_laui,
                )

            else:
                overridden_keys = overridden_keys_dict["root"]

                if isinstance(value, dict):
                    if not target.get(key):
                        target[key] = {}
                    if not target_value_sources.get(key):
                        target_value_sources[key] = {}
                    if not overridden_keys_dict.get(key):
                        overridden_keys_dict[key] = {"root": []}

                    if key not in overridden_keys or isinstance(target[key], dict):
                        self._merge_content(
                            source=value,
                            target=target[key],
                            target_value_sources=target_value_sources[key],
                            source_laui=source_laui,
                            overridden_keys_dict=overridden_keys_dict[key],
                        )
                        overridden_keys_dict["root"].append(key)

                    else:
                        log_warning(
                            "api",
                            "ConfigManager",
                            "_merge_content",
                            f"Key '{key}' ignored - overridden in previous config",
                        )

                elif key not in overridden_keys:
                    target[key] = value
                    target_value_sources[key] = source_laui
                    overridden_keys_dict["root"].append(key)

                else:
                    log_warning(
                        "api",
                        "ConfigManager",
                        "_merge_content",
                        f"Key '{key}' ignored - already set by previous workflow config",
                    )

    def replace_placeholders(
        self,
        payload_content: str | dict[str, Any] | list,
        parameters: dict[str, Any],
        task: TaskValidationModel | None = None,
    ) -> str | dict[str, Any] | list:
        if task:
            task_system_params = task.model_dump(
                exclude={"description", "actions", "payload", "config"}, mode="python"
            )
            parameters = {**task_system_params, **parameters}

        if isinstance(payload_content, dict):
            return {
                key: self.replace_placeholders(value, parameters)
                for key, value in payload_content.items()
            }

        elif isinstance(payload_content, list):
            return [self.replace_placeholders(item, parameters) for item in payload_content]

        elif isinstance(payload_content, str):
            if "{{" not in payload_content:
                return payload_content

            try:
                env = Environment(undefined=KeepUndefined)
                template = env.from_string(payload_content)
                return template.render(**parameters)
            except Exception as e:
                log_error(
                    "api",
                    "ConfigManager",
                    "replace_placeholders",
                    f"Failed to render template '{payload_content}': {e}",
                )
                return payload_content

        else:
            return payload_content

    def get_builtin_variables(self, logical_date: datetime | None = None) -> dict[str, Any]:
        """
        This function is used to define system Variables - such as {{ds}} , {{ts}} , {{logical_date}}, etc
        Mirrors Airflow template variables derived from the task's logical_date.
        """
        now = datetime.now(UTC)

        if logical_date is None:
            return {
                "ds": None,
                "ds_nodash": None,
                "ts": None,
                "ts_nodash_with_tz": None,
                "ts_nodash": None,
                "current_date": now.strftime("%Y-%m-%d"),
                "current_timestamp": now.isoformat(),
            }

        dt = logical_date

        return {
            "ds": dt.strftime("%Y-%m-%d"),
            "ds_nodash": dt.strftime("%Y%m%d"),
            "ts": dt.isoformat(),
            "ts_nodash_with_tz": dt.strftime("%Y%m%dT%H%M%S")
            + (dt.strftime("%z") if dt.tzinfo else "+0000"),
            "ts_nodash": dt.strftime("%Y%m%dT%H%M%S"),
            "current_date": now.strftime("%Y-%m-%d"),
            "current_timestamp": now.isoformat(),
        }

    def process_task_execution(
        self, task: TaskValidationModel, field: str = None
    ) -> TaskValidationModel:
        """
        This is the main function for task parameter replacement.
        This function takes a task with already merged config and replaces all placeholders
        in the payload with builtin variables and config parameters.
        """
        # Get builtin system variables (ds, ts, etc)
        builtin_vars = self.get_builtin_variables(getattr(task, "logical_date", None))

        # Get parameters from task.config (already merged)
        config_parameters = task.config.get("parameters", {})

        # Combine builtin vars and config parameters (builtin vars take precedence)
        all_parameters = {**config_parameters, **builtin_vars}

        if field:
            if field == "payload" and task.payload:
                task.payload = self.replace_placeholders(task.payload, all_parameters, task=task)
            if field == "actions" and task.actions:
                task.actions = self.replace_placeholders(task.actions, all_parameters, task=task)
        else:
            # Replace placeholders in payload and actions
            if task.payload:
                task.payload = self.replace_placeholders(task.payload, all_parameters, task=task)
            if task.actions:
                task.actions = self.replace_placeholders(task.actions, all_parameters, task=task)

        return task
