# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
payload = '''
{
  "source_table_name": "int_absent_badges",
  "chat_prompt": "Generate a professional HTML absence summary report from this data. Title: Absence Summary Report. Include two sections: (1) A department summary table showing: department, person_type, total_absence_days, distinct_badges_absent, avg_absences_per_badge — sorted by total_absence_days DESC. Use a red header (#C62828 white text). Highlight the top 3 departments with highest absences in light red (#FFEBEE). (2) A detailed absence table showing: badge_id, name, department, person_type, event_date — sorted by event_date DESC then department. Highlight teachers (person_type = teacher) in light blue (#E3F2FD). Add a summary card at the top showing: total absence records, distinct badges absent, date range, and most absent department."
}
'''
