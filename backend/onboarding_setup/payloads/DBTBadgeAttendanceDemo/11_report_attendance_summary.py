# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
payload = '''
{
  "source_table_name": "mart_attendance_summary",
  "chat_prompt": "Generate a professional HTML comprehensive attendance summary report from this data. Title: Daily Attendance Summary. Include four sections: (1) Summary cards showing: report_date, total people, present count, absent count, overall attendance percentage, count still on campus, count early exits, count with absence streaks >= 3. (2) Department breakdown table: department, present_count, absent_count, attendance_pct, avg_total_hours — sorted by attendance_pct ASC. Use a navy header (#1A237E white text). (3) Flags table showing badges with any of: still_on_campus = true, early_exit = true, absence_streak_days >= 3 — columns: name, department, person_type, attendance_status, still_on_campus, early_exit, absence_streak_days. Highlight still_on_campus in orange (#FFF3E0), early_exit in yellow (#FFFDE7), absence_streak >= 3 in red (#FFEBEE). (4) Full attendance table: name, department, person_type, attendance_status, total_hours (2 dp), first_in_time (HH:MM), last_out_time (HH:MM), avg_session_hours (2 dp) — sorted by attendance_status DESC then department. Absent rows in light red (#FFEBEE), present rows with hours > 8 in light green (#E8F5E9)."
}
'''
