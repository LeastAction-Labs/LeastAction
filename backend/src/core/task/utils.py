# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from datetime import UTC, datetime

from croniter import croniter


def calculate_logical_date(frequency: str, logical_date: datetime | None) -> datetime | None:
    if frequency == "ADHOC":
        return None

    try:
        cron = croniter(frequency, logical_date)
        next_run = cron.get_next(datetime)
        return next_run.replace(second=0, microsecond=0)
    except Exception as e:
        raise ValueError(f"Invalid cron expression: {frequency}") from e


def calculate_next_run_date(frequency: str, task_start_time: datetime | None) -> datetime | None:
    if frequency == "ADHOC":
        return None
    base = task_start_time if task_start_time is not None else datetime.now(UTC)
    try:
        cron = croniter(frequency, base)
        next_run = cron.get_next(datetime)
    except Exception as e:
        raise ValueError(f"Invalid cron expression: {frequency}") from e
    return next_run.replace(second=0, microsecond=0)
