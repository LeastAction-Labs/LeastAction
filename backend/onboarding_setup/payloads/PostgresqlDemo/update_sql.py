# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
payload = '''UPDATE people SET age = CASE name WHEN 'Alice' THEN 29 WHEN 'Bob' THEN 35 WHEN 'Charlie' THEN 23 END, logical_date = '{{ logical_date }}' WHERE name IN ('Alice', 'Bob', 'Charlie');'''

prompt = "PostgreSQL UPDATE payload for the demo 'people' table. Uses CASE statement to update ages and sets logical_date to the workflow partition date."

install_docs = "Used with PostgresqlExecuteSQL operator. Run after insert_sql.py."

guide_docs = "Updates ages for Alice (29), Bob (35), Charlie (23) and refreshes logical_date in the demo 'people' table."

description = "PostgreSQL DML payload — updates demo rows in 'people' table with new ages and logical_date."

publisher = "LeastAction"

metadata = {
    "service": "PostgreSQL",
    "category": "Demo",
    "tags": ["postgresql", "update", "dml", "demo", "payload"]
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}

