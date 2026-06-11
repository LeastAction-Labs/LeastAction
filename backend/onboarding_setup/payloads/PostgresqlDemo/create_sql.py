# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
payload = '''CREATE TABLE IF NOT EXISTS people (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    age INT,
    logical_date DATE
);
'''

prompt = "PostgreSQL DDL payload to create the 'people' demo table. Used with PostgresqlExecuteSQL operator as the first step in the demo workflow."

install_docs = """# create_sql Payload — Setup

Used with PostgresqlExecuteSQL operator. Run this first to create the demo table before
running insert_sql or update_sql payloads.
"""

guide_docs = "Creates the 'people' table with id (PK), name, age, and logical_date columns."

description = "PostgreSQL DDL payload — creates demo 'people' table for the PostgreSQL workflow demo."

publisher = "LeastAction"

metadata = {
    "service": "PostgreSQL",
    "category": "Demo",
    "tags": ["postgresql", "ddl", "create", "table", "demo", "payload"]
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}

