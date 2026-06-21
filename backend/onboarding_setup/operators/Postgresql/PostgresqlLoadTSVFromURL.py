# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Source License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
operator_type = "postgresql"

codeblock = {"main.py": '''
import json
import gzip
import csv
import io
import urllib.request
import psycopg2

from src.common.logger.logger import log_info, log_error


def initialize(task):
    conn_config = task.get("connection", {})
    return psycopg2.connect(
        host=conn_config.get("host", "localhost"),
        port=conn_config.get("port", 5432),
        database=conn_config.get("database"),
        user=conn_config.get("user"),
        password=conn_config.get("password"),
        connect_timeout=30,
    )


def run(task, conn):
    payload = task.get("payload", "")
    if isinstance(payload, str):
        config = json.loads(payload)
    else:
        config = payload

    cursor = conn.cursor()

    schema_setup = config.get("schema_setup", "")
    if isinstance(schema_setup, list):
        stmts = schema_setup
    else:
        stmts = [s.strip() for s in schema_setup.split(";") if s.strip()]

    for stmt in stmts:
        cursor.execute(stmt)
    conn.commit()
    log_info("task", "run", "schema_setup_done", "Schema setup complete")

    total_rows = 0

    for table_cfg in config.get("tables", []):
        url = table_cfg["url"]
        target_table = table_cfg["target_table"]
        drop_first = table_cfg.get("drop_first", True)
        create_ddl = table_cfg.get("create_ddl", "")
        tsv_columns = table_cfg["tsv_columns"]
        target_columns = table_cfg.get("target_columns", tsv_columns)
        filter_col = table_cfg.get("filter_column")
        filter_vals = set(table_cfg.get("filter_values") or [])
        max_rows = table_cfg.get("max_rows")
        batch_size = table_cfg.get("batch_size", 5000)

        if drop_first:
            cursor.execute(f"DROP TABLE IF EXISTS {target_table}")
            conn.commit()

        if create_ddl:
            cursor.execute(create_ddl)
            conn.commit()

        log_info("task", "run", "downloading", f"Downloading {url}")
        req = urllib.request.Request(url, headers={"User-Agent": "LeastAction/1.0"})
        with urllib.request.urlopen(req, timeout=300) as response:
            raw_bytes = response.read()
        log_info("task", "run", "downloaded", f"Downloaded {len(raw_bytes)} bytes")

        placeholders = ",".join(["%s"] * len(target_columns))
        col_list = ",".join(target_columns)
        insert_sql = f"INSERT INTO {target_table} ({col_list}) VALUES ({placeholders})"

        batch = []
        rows_loaded = 0

        with gzip.open(io.BytesIO(raw_bytes), "rt", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter="\\t")
            for row in reader:
                if filter_col and filter_vals and row.get(filter_col) not in filter_vals:
                    continue

                values = [
                    None if row.get(col, "\\\\N") == "\\\\N" else row.get(col)
                    for col in tsv_columns
                ]
                batch.append(values)

                if len(batch) >= batch_size:
                    cursor.executemany(insert_sql, batch)
                    conn.commit()
                    rows_loaded += len(batch)
                    log_info("task", "run", "batch_inserted", f"{target_table}: {rows_loaded} rows")
                    batch = []

                if max_rows and rows_loaded >= max_rows:
                    break

            if batch:
                cursor.executemany(insert_sql, batch)
                conn.commit()
                rows_loaded += len(batch)

        log_info("task", "run", "table_done", f"{target_table}: {rows_loaded} total rows loaded")
        total_rows += rows_loaded

    cursor.close()
    return {
        "execution_type": "sync",
        "status": "success",
        "result": {"total_rows_loaded": total_rows},
    }


def check_completion(task, conn, run_details):
    if run_details.get("status") == "success":
        return {
            "status": "success",
            "message": "TSV data loaded successfully",
            "output": run_details.get("result", {}),
        }
    return {
        "status": "failed",
        "message": run_details.get("error", "Unknown error"),
        "output": {},
    }


def finish(task, conn, completion, run_details):
    if conn:
        try:
            conn.close()
        except Exception:
            pass
'''}

bashblock = {"main.sh": """
#!/bin/bash
pip install psycopg2-binary==2.9.*
python3 -c "import psycopg2; print(f'psycopg2 version: {psycopg2.__version__}')"
echo "Dependencies installed successfully"
"""}

connection = {
    "host": "localhost",
    "port": 5432,
    "database": "mydb",
    "user": "postgres",
    "password": "your_password_here",
}

payload = """
{
  "schema_setup": "CREATE SCHEMA IF NOT EXISTS imdb_base",
  "tables": [
    {
      "url": "https://datasets.imdbws.com/title.basics.tsv.gz",
      "target_table": "imdb_base.title_basics",
      "drop_first": true,
      "create_ddl": "CREATE TABLE imdb_base.title_basics (tconst VARCHAR(20), title_type VARCHAR(50), primary_title TEXT, original_title TEXT, is_adult VARCHAR(5), start_year VARCHAR(10), end_year VARCHAR(10), runtime_minutes VARCHAR(10), genres TEXT)",
      "tsv_columns": ["tconst","titleType","primaryTitle","originalTitle","isAdult","startYear","endYear","runtimeMinutes","genres"],
      "target_columns": ["tconst","title_type","primary_title","original_title","is_adult","start_year","end_year","runtime_minutes","genres"],
      "filter_column": "tconst",
      "filter_values": ["tt0120737","tt0816692","tt1375666","tt0468569","tt0137523"],
      "max_rows": null,
      "batch_size": 5000
    }
  ]
}
"""

prompt = (
    "Download one or more gzip-compressed TSV files from public URLs, filter rows, "
    "and batch-insert into PostgreSQL. Uses Python stdlib only (gzip, csv, io, urllib). "
    "Payload is JSON: schema_setup (SQL string or list), tables[] each with url, target_table, "
    "drop_first, create_ddl, tsv_columns, target_columns, filter_column, filter_values, "
    "max_rows, batch_size. Converts IMDB null sentinel \\N to SQL NULL. "
    "Set task timeout >= 600 seconds for large files."
)

install_docs = """# PostgresqlLoadTSVFromURL — Install Guide

## Dependencies
    pip install psycopg2-binary==2.9.*

No other dependencies — uses Python stdlib (gzip, csv, io, urllib).

## Notes
- Set task timeout to at least 600 seconds for large files (IMDB basics ~100 MB compressed)
- filter_column + filter_values performs row-level filtering while streaming the file
- IMDB \\N sentinel is automatically converted to SQL NULL
"""

guide_docs = """# PostgresqlLoadTSVFromURL — Operator Guide

## What it does

Downloads a gzip-compressed TSV file from a URL, optionally filters rows by a column value,
and batch-inserts matching rows into a PostgreSQL table. Designed for loading public datasets
like IMDB title.basics.tsv.gz and title.ratings.tsv.gz.

---

## Payload (JSON)

    {
      "schema_setup": "CREATE SCHEMA IF NOT EXISTS imdb_base",
      "tables": [
        {
          "url": "https://datasets.imdbws.com/title.basics.tsv.gz",
          "target_table": "imdb_base.title_basics",
          "drop_first": true,
          "create_ddl": "CREATE TABLE imdb_base.title_basics (tconst VARCHAR(20), ...)",
          "tsv_columns": ["tconst", "titleType", "primaryTitle", ...],
          "target_columns": ["tconst", "title_type", "primary_title", ...],
          "filter_column": "tconst",
          "filter_values": ["tt0120737", "tt0816692"],
          "max_rows": null,
          "batch_size": 5000
        }
      ]
    }

- schema_setup: SQL string (semicolon-separated) or list of SQL statements to run first
- filter_column + filter_values: only insert rows matching filter_values in filter_column
- tsv_columns: column names in the TSV header (input order)
- target_columns: corresponding PostgreSQL column names
- max_rows: hard limit on rows inserted (null = no limit)

---

## IMDB null handling

IMDB uses \\N as a null sentinel. This operator converts \\N → SQL NULL automatically.

---

## Output (on success)

    {
      "total_rows_loaded": 15
    }
"""

description = """
Downloads gzip-compressed TSV files from public URLs and batch-inserts into PostgreSQL.
Supports row-level filtering, schema setup, IMDB \\N-to-NULL conversion, and configurable
batch sizes. Uses Python stdlib only — no external HTTP libraries required. Designed for
loading IMDB datasets and similar public TSV data sources into a PostgreSQL data warehouse.
"""

publisher = "LeastAction"

metadata = {
    "service": "PostgreSQL",
    "category": "Ingestion",
    "tags": ["postgresql", "tsv", "imdb", "load", "ingest", "gzip", "url", "batch"],
}

version_details = {
    "version": "0.0.1",
    "core": ["0.*"],
}
