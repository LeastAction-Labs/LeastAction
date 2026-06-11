# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
payload = '''
{
  "source_table_name": "mart_attendance_summary",
  "chat_prompt": "Generate a professional HTML student-only attendance report from this data. Filter to only rows where person_type = 'student'. Title: Student Attendance Report. Include three sections: (1) Summary cards showing: total students, present count, absent count, student attendance percentage, count with absence streaks >= 3, count with early exits. (2) A department breakdown table showing department, present_count, absent_count, attendance_pct, avg_total_hours — sorted by attendance_pct ASC. Use a purple header (#6A1B9A white text). (3) A detailed student table with columns: name, department, year_or_sem (if available, else omit), attendance_status, total_hours (rounded to 2 decimal places), first_in_time (HH:MM), last_out_time (HH:MM), early_exit, absence_streak_days — sorted by absence_streak_days DESC then attendance_status. Highlight absent students in light red (#FFEBEE). Highlight students with absence_streak_days >= 3 in orange (#FFF3E0) with bold badge_id. Highlight early_exit = true in light yellow (#FFFDE7). Add a footer showing the report_date."
}
'''
