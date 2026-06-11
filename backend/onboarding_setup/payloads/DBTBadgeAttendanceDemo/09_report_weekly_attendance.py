# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
payload = '''
{
  "source_table_name": "fct_attendance_weekly",
  "chat_prompt": "Generate a professional HTML weekly attendance report from this data. Title: Weekly Attendance Report. Show a table with columns: badge_id, week_start_date, week_end_date, year, week_of_year, total_hours (rounded to 2 decimal places), total_sessions, days_present, earliest_in (time only HH:MM), latest_out (time only HH:MM), avg_session_hours (rounded to 2 decimal places). Sort by week_start_date DESC then days_present ASC. Use a teal header (#00796B white text). Highlight rows where days_present < 3 in light orange (#FFF3E0) with a note icon. Highlight rows where total_hours > 40 in light green (#E8F5E9). Add a summary section showing: average days_present across all badges and weeks, average total_hours per week, count of badges with days_present < 3 in the latest week. Include a subtitle showing the week range covered."
}
'''
