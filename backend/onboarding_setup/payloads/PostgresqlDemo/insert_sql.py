# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
payload = '''INSERT INTO people (name, age, logical_date) VALUES ('Alice', 28, '{{ logical_date }}'), ('Bob', 34, '{{ logical_date }}'), ('Charlie', 22, '{{ logical_date }}');'''

prompt = "PostgreSQL INSERT payload for the demo 'people' table. Uses {{ logical_date }} template variable for date partitioning."

install_docs = "Used with PostgresqlExecuteSQL operator. Run after create_sql.py."

guide_docs = "Inserts 3 demo rows (Alice, Bob, Charlie) into the 'people' table with the workflow's logical_date."

description = "PostgreSQL DML payload — inserts sample rows into demo 'people' table with logical_date partitioning."

publisher = "LeastAction"

metadata = {
    "service": "PostgreSQL",
    "category": "Demo",
    "tags": ["postgresql", "insert", "dml", "demo", "payload"]
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}

