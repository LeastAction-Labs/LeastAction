# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from datetime import datetime, timedelta

from src.common.logger.logger import log_warning


def ds_add(date_str: str, days: int, format: str = "%Y-%m-%d") -> str | None:

    try:
        date_obj = datetime.strptime(date_str, format)
        new_date = date_obj + timedelta(days=days)
        return new_date.strftime(format)
    except Exception as e:
        log_warning("API", "DatetimeMacros", "ds_add", f"Error: {e}")
        return None


def ds_format(date_str: str, input_format: str, output_format: str) -> str | None:
    """Convert date string from one format to another."""
    # Implementation similar pattern


def now(format: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Get current datetime as string."""
    # Implementation


def today(format: str = "%Y-%m-%d") -> str:
    """Get current date as string."""
    # Implementation
