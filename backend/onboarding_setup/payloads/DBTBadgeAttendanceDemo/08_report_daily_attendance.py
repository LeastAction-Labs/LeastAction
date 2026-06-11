# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
payload = '''
{
  "source_table_name": "fct_attendance_daily",
  "chat_prompt": "Generate a professional HTML attendance report from this data. Title: Daily Attendance Report. Show a table with columns: badge_id, full_date, total_hours (rounded to 2 decimal places), total_sessions, first_in_time (time only, HH:MM), last_out_time (time only, HH:MM), avg_session_hours (rounded to 2 decimal places). Sort by full_date DESC then total_hours DESC. Use a blue header (#1565C0 white text). Highlight rows where total_hours > 8 in light green (#E8F5E9). Highlight rows where total_sessions = 0 in light red (#FFEBEE). Add a summary row at the bottom showing: average total_hours, total sessions count, and count of distinct badge_ids. Include a subtitle showing the date range covered."
}
'''
