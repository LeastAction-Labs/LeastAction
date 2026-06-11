# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import inspect
import json
import time
import traceback
from collections.abc import Callable
from functools import wraps

import psutil

from src.common.logger.logger import log_info


def get_system_resources() -> dict:
    """Snapshot CPU and memory stats for the current process and system."""
    process = psutil.Process()
    mem_info = process.memory_info()
    vm = psutil.virtual_memory()
    return {
        "cpu_percent_system": psutil.cpu_percent(interval=None),
        "cpu_percent_process": process.cpu_percent(interval=None),
        "memory_rss_mb": round(mem_info.rss / 1024 / 1024, 2),
        "memory_vms_mb": round(mem_info.vms / 1024 / 1024, 2),
        "memory_system_used_pct": vm.percent,
        "memory_system_available_mb": round(vm.available / 1024 / 1024, 2),
    }


def performance_logger(func: Callable) -> Callable:
    """
    Performance decorator that logs function execution time plus CPU and
    memory usage (process + system) via the existing PERFORMANCE category.
    """

    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        start_time = time.time()
        caught_error: str | None = None
        try:
            result = await func(*args, **kwargs)
            return result
        except Exception:
            caught_error = traceback.format_exc()
            raise
        finally:
            execution_time = time.time() - start_time
            _log_performance(func.__name__, execution_time, caught_error)

    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        start_time = time.time()
        caught_error: str | None = None
        try:
            result = func(*args, **kwargs)
            return result
        except Exception:
            caught_error = traceback.format_exc()
            raise
        finally:
            execution_time = time.time() - start_time
            _log_performance(func.__name__, execution_time, caught_error)

    if inspect.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


def _log_performance(function_name: str, execution_time: float, error: str | None = None) -> None:
    """Log performance using the existing logger system."""
    try:
        message: dict = {"execution_time": execution_time}
        if error is not None:
            message["error"] = error
        log_info(
            category="PERFORMANCE",
            operation=function_name,
            step="performance_measurement",
            message=json.dumps(message),
        )
    except Exception as e:
        # Silently fail to avoid breaking the application
        print(f"Performance logging failed for {function_name}: {e}")
