# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
# Experimental Preview — multi-database read-only inspect endpoint.
# connection.AWS  → Athena | Redshift | S3 (DuckDB)
# connection.gcp  → BigQuery | GCS (DuckDB)
# connection.azure→ Azure Blob (DuckDB)
# connection.postgresql / connection.mysql — direct drivers
import asyncio
import json
import re
import time

import psycopg2
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from pydantic_mongo import PydanticObjectId

from src.core.catalog.orchestrator import ItemOrchestrator, get_item_orchestrator

query_router = APIRouter()

_ROW_LIMIT = 10_000
_DUCKDB_MEMORY = "512MB"  # per-query cap; prevents OOM on large S3/GCS/Azure scans
_DUCKDB_THREADS = 2  # prevent CPU starvation on the shared server

# ── SQL validation ─────────────────────────────────────────────────────────────

_ALLOWED_PREFIXES = ("select", "with", "explain")
_BLOCKED_KEYWORDS = (
    "insert",
    "update",
    "delete",
    "drop",
    "create",
    "alter",
    "truncate",
    "grant",
    "revoke",
    "execute",
    "call",
    "copy",
    "vacuum",
    "analyze",
    "cluster",
    "reindex",
    "lock",
)
_COMMENT_RE = re.compile(r"--[^\n]*|/\*.*?\*/", re.DOTALL)


def _validate_sql(sql: str) -> None:
    cleaned = _COMMENT_RE.sub(" ", sql)
    normalized = " ".join(cleaned.split()).lower()
    if not any(normalized.startswith(p) for p in _ALLOWED_PREFIXES):
        raise HTTPException(
            status_code=400, detail="Only SELECT / WITH / EXPLAIN queries are allowed."
        )
    if ";" in normalized:
        raise HTTPException(
            status_code=400,
            detail="Multiple statements are not permitted i.e ';' is not permitted.",
        )
    for kw in _BLOCKED_KEYWORDS:
        if re.search(rf"\b{kw}\b", normalized):
            raise HTTPException(status_code=400, detail=f"Keyword '{kw.upper()}' is not permitted.")


# ── Field synonym maps (first match wins) ──────────────────────────────────────

_PG_SYNONYMS: dict[str, list[str]] = {
    "host": ["host", "hostname", "server", "db_host", "pg_host"],
    "port": ["port", "db_port", "pg_port"],
    "database": ["database", "dbname", "db", "db_name", "schema"],
    "user": ["user", "username", "usr", "login", "db_user"],
    "password": ["password", "pass", "passwd", "pwd", "secret"],
}

_MYSQL_SYNONYMS: dict[str, list[str]] = {
    "host": ["host", "hostname", "server", "db_host", "mysql_host"],
    "port": ["port", "db_port", "mysql_port"],
    "database": ["database", "dbname", "db", "db_name", "schema"],
    "user": ["user", "username", "usr", "login", "db_user"],
    "password": ["password", "pass", "passwd", "pwd", "secret"],
    "charset": ["charset", "encoding", "character_set"],
}

_AWS_SYNONYMS: dict[str, list[str]] = {
    "region": ["region", "aws_region", "region_name"],
    "access_key": ["aws_access_key_id", "access_key", "access_key_id", "key_id"],
    "secret_key": ["aws_secret_access_key", "secret_key", "secret_access_key", "secret"],
    "session_token": ["aws_session_token", "session_token", "token"],
    "role_arn": ["assume_iam_role", "role_arn", "iam_role", "role"],
    "output_location": ["output_location", "s3_output", "s3_path", "result_location", "output_s3"],
    "workgroup": ["workgroup", "work_group", "athena_workgroup"],
    "database": ["database", "db", "db_name", "athena_database"],
    "cluster_identifier": ["cluster_identifier", "cluster_id", "redshift_cluster"],
    "workgroup_name": ["workgroup_name", "serverless_workgroup", "rs_workgroup"],
}

_BQ_SYNONYMS: dict[str, list[str]] = {
    "project": ["project", "project_id", "gcp_project", "bq_project", "google_project"],
    "credentials": [
        "credentials_json",
        "service_account",
        "service_account_key",
        "credentials",
        "gcp_credentials",
        "key_json",
    ],
    "dataset": ["dataset", "dataset_id", "bq_dataset", "default_dataset"],
    "location": ["location", "region", "bq_location"],
}

_GCS_SYNONYMS: dict[str, list[str]] = {
    "access_key": ["hmac_access_key", "access_key", "gcs_access_key"],
    "secret_key": ["hmac_secret", "secret_key", "gcs_secret"],
    "endpoint": ["endpoint", "gcs_endpoint"],
}

_AZURE_SYNONYMS: dict[str, list[str]] = {
    "connection_string": [
        "connection_string",
        "azure_connection_string",
        "storage_connection_string",
    ],
    "account_name": ["account_name", "storage_account", "azure_account"],
    "account_key": ["account_key", "storage_key", "azure_key"],
}


def _pick(data: dict, param: str, synonyms: dict[str, list[str]], default=None):
    for key in synonyms.get(param, []):
        if key in data:
            return data[key]
    return default


# ── Driver implementations ─────────────────────────────────────────────────────


def _execute_postgresql(data: dict, sql: str) -> tuple[list[str], list[list]]:
    host = _pick(data, "host", _PG_SYNONYMS, "localhost")
    port = int(_pick(data, "port", _PG_SYNONYMS, 5432))
    database = _pick(data, "database", _PG_SYNONYMS, "")
    user = _pick(data, "user", _PG_SYNONYMS, "")
    password = _pick(data, "password", _PG_SYNONYMS, "")
    if not database or not user:
        raise HTTPException(
            status_code=400,
            detail=f"PostgreSQL connection missing database/user. Got keys: {list(data.keys())}",
        )
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            dbname=database,
            user=user,
            password=password,
            connect_timeout=10,
            options="-c statement_timeout=120000",
        )
        conn.set_session(readonly=True, autocommit=True)
        with conn.cursor() as cur:
            cur.execute(sql)
            columns = [d[0] for d in (cur.description or [])]
            rows = [list(r) for r in (cur.fetchmany(_ROW_LIMIT + 1) or [])]
        conn.close()
        return columns, rows
    except psycopg2.OperationalError as e:
        raise HTTPException(status_code=502, detail=f"Cannot connect to PostgreSQL: {e}")
    except psycopg2.Error as e:
        raise HTTPException(
            status_code=400, detail=f"PostgreSQL query error: {e.pgerror or str(e)}"
        )


def _execute_mysql(data: dict, sql: str) -> tuple[list[str], list[list]]:
    try:
        import pymysql
    except ImportError:
        raise HTTPException(
            status_code=501, detail="pymysql not installed — add pymysql to backend dependencies."
        )
    host = _pick(data, "host", _MYSQL_SYNONYMS, "localhost")
    port = int(_pick(data, "port", _MYSQL_SYNONYMS, 3306))
    database = _pick(data, "database", _MYSQL_SYNONYMS, "")
    user = _pick(data, "user", _MYSQL_SYNONYMS, "")
    password = _pick(data, "password", _MYSQL_SYNONYMS, "")
    charset = _pick(data, "charset", _MYSQL_SYNONYMS, "utf8mb4")
    if not database or not user:
        raise HTTPException(
            status_code=400,
            detail=f"MySQL connection missing database/user. Got keys: {list(data.keys())}",
        )
    try:
        conn = pymysql.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
            charset=charset,
            connect_timeout=10,
            cursorclass=pymysql.cursors.SSCursor,  # streaming — fetchmany limits server transfer
        )
        with conn.cursor() as cur:
            cur.execute(sql)
            columns = [d[0] for d in (cur.description or [])]
            rows = [list(r) for r in (cur.fetchmany(_ROW_LIMIT + 1) or [])]
        conn.close()
        return columns, rows
    except pymysql.OperationalError as e:
        raise HTTPException(status_code=502, detail=f"Cannot connect to MySQL: {e}")
    except pymysql.Error as e:
        raise HTTPException(status_code=400, detail=f"MySQL query error: {e}")


def _build_boto3_session(data: dict):
    import boto3

    region = _pick(data, "region", _AWS_SYNONYMS, "us-east-1")
    access_key = _pick(data, "access_key", _AWS_SYNONYMS)
    secret_key = _pick(data, "secret_key", _AWS_SYNONYMS)
    session_tok = _pick(data, "session_token", _AWS_SYNONYMS)
    role_arn = _pick(data, "role_arn", _AWS_SYNONYMS)

    if access_key and secret_key:
        return boto3.Session(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            aws_session_token=session_tok,
            region_name=region,
        )
    if role_arn:
        sts = boto3.client("sts", region_name=region)
        creds = sts.assume_role(RoleArn=role_arn, RoleSessionName="la_query")["Credentials"]
        return boto3.Session(
            aws_access_key_id=creds["AccessKeyId"],
            aws_secret_access_key=creds["SecretAccessKey"],
            aws_session_token=creds["SessionToken"],
            region_name=region,
        )
    return boto3.Session(region_name=region)


def _execute_athena(data: dict, sql: str) -> tuple[list[str], list[list]]:
    output_location = _pick(data, "output_location", _AWS_SYNONYMS)
    database = _pick(data, "database", _AWS_SYNONYMS, "default")
    workgroup = _pick(data, "workgroup", _AWS_SYNONYMS, "primary")
    if not output_location:
        raise HTTPException(
            status_code=400,
            detail="Athena connection missing output_location (S3 path for results).",
        )
    try:
        session = _build_boto3_session(data)
        client = session.client("athena")
        resp = client.start_query_execution(
            QueryString=sql,
            ResultConfiguration={"OutputLocation": output_location},
            QueryExecutionContext={"Database": database},
            WorkGroup=workgroup,
        )
        qid = resp["QueryExecutionId"]
        for _ in range(60):
            time.sleep(2)
            status = client.get_query_execution(QueryExecutionId=qid)["QueryExecution"]["Status"]
            state = status["State"]
            if state == "SUCCEEDED":
                break
            if state in ("FAILED", "CANCELLED"):
                reason = status.get("StateChangeReason", "unknown")
                raise HTTPException(status_code=400, detail=f"Athena query {state}: {reason}")
        else:
            raise HTTPException(status_code=504, detail="Athena query timed out after 120s.")

        columns: list[str] = []
        rows: list[list] = []
        paginator = client.get_paginator("get_query_results")
        done = False
        for page_idx, page in enumerate(paginator.paginate(QueryExecutionId=qid)):
            result_rows = page["ResultSet"]["Rows"]
            if page_idx == 0:
                columns = [c["VarCharValue"] for c in result_rows[0]["Data"]]
                result_rows = result_rows[1:]
            for row in result_rows:
                rows.append([c.get("VarCharValue") for c in row["Data"]])
                if len(rows) >= _ROW_LIMIT + 1:
                    done = True
                    break
            if done:
                break
        return columns, rows
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Athena error: {e}")


def _execute_redshift(data: dict, sql: str) -> tuple[list[str], list[list]]:
    database = _pick(data, "database", _AWS_SYNONYMS, "")
    cluster_id = _pick(data, "cluster_identifier", _AWS_SYNONYMS)
    workgroup_name = _pick(data, "workgroup_name", _AWS_SYNONYMS)
    if not database:
        raise HTTPException(status_code=400, detail="Redshift connection missing database field.")
    if not cluster_id and not workgroup_name:
        raise HTTPException(
            status_code=400,
            detail="Redshift connection missing cluster_identifier or workgroup_name.",
        )
    try:
        session = _build_boto3_session(data)
        client = session.client("redshift-data")
        kwargs = {"Sql": sql, "Database": database}
        if cluster_id:
            kwargs["ClusterIdentifier"] = cluster_id
        else:
            kwargs["WorkgroupName"] = workgroup_name
        stmt_id = client.execute_statement(**kwargs)["Id"]
        for _ in range(60):
            time.sleep(2)
            desc = client.describe_statement(Id=stmt_id)
            status = desc["Status"]
            if status == "FINISHED":
                break
            if status in ("FAILED", "ABORTED"):
                raise HTTPException(
                    status_code=400, detail=f"Redshift query {status}: {desc.get('Error', '')}"
                )
        else:
            raise HTTPException(status_code=504, detail="Redshift query timed out after 120s.")

        def _val(field: dict):
            if field.get("isNull"):
                return None
            for k in ("stringValue", "longValue", "doubleValue", "booleanValue", "blobValue"):
                if k in field:
                    return field[k]
            return None

        columns: list[str] = []
        rows: list[list] = []
        paginator = client.get_paginator("get_statement_result")
        done = False
        for page_idx, page in enumerate(paginator.paginate(Id=stmt_id)):
            if page_idx == 0:
                columns = [c["label"] for c in page["ColumnMetadata"]]
            for row in page["Records"]:
                rows.append([_val(f) for f in row])
                if len(rows) >= _ROW_LIMIT + 1:
                    done = True
                    break
            if done:
                break
        return columns, rows
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Redshift error: {e}")


def _execute_aws(data: dict, sql: str) -> tuple[list[str], list[list]]:
    if _pick(data, "output_location", _AWS_SYNONYMS):
        return _execute_athena(data, sql)
    if _pick(data, "cluster_identifier", _AWS_SYNONYMS) or _pick(
        data, "workgroup_name", _AWS_SYNONYMS
    ):
        return _execute_redshift(data, sql)
    # No Athena/Redshift fields — treat as plain S3 connection (DuckDB)
    return _execute_duckdb_s3(data, sql)


def _execute_bigquery(data: dict, sql: str) -> tuple[list[str], list[list]]:
    try:
        from google.cloud import bigquery
        from google.oauth2 import service_account
    except ImportError:
        raise HTTPException(status_code=501, detail="google-cloud-bigquery not installed.")
    project = _pick(data, "project", _BQ_SYNONYMS)
    creds_raw = _pick(data, "credentials", _BQ_SYNONYMS)
    location = _pick(data, "location", _BQ_SYNONYMS, "US")
    if not project:
        raise HTTPException(
            status_code=400,
            detail=f"BigQuery connection missing project. Got keys: {list(data.keys())}",
        )
    try:
        creds = None
        if creds_raw:
            info = creds_raw if isinstance(creds_raw, dict) else json.loads(creds_raw)
            creds = service_account.Credentials.from_service_account_info(
                info, scopes=["https://www.googleapis.com/auth/bigquery.readonly"]
            )
        client = bigquery.Client(project=project, credentials=creds, location=location)
        job = client.query(
            sql, job_config=bigquery.QueryJobConfig(maximum_bytes_billed=10 * 1024**3)
        )
        result = job.result(timeout=119)
        columns = [f.name for f in result.schema]
        rows: list[list] = []
        for row in result:
            rows.append(list(row.values()))
            if len(rows) >= _ROW_LIMIT + 1:
                break
        return columns, rows
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"BigQuery error: {e}")


def _execute_gcp(data: dict, sql: str) -> tuple[list[str], list[list]]:
    # BigQuery: has a project field. GCS: has HMAC keys, no project.
    if _pick(data, "project", _BQ_SYNONYMS):
        return _execute_bigquery(data, sql)
    return _execute_duckdb_gcs(data, sql)


def _execute_duckdb_s3(data: dict, sql: str) -> tuple[list[str], list[list]]:
    import duckdb

    con = duckdb.connect()
    try:
        con.execute(f"SET memory_limit='{_DUCKDB_MEMORY}'; SET threads={_DUCKDB_THREADS};")
        con.execute("INSTALL httpfs; LOAD httpfs;")
        access_key = _pick(data, "access_key", _AWS_SYNONYMS)
        secret_key = _pick(data, "secret_key", _AWS_SYNONYMS)
        session_tok = _pick(data, "session_token", _AWS_SYNONYMS)
        region = _pick(data, "region", _AWS_SYNONYMS, "us-east-1")
        role_arn = _pick(data, "role_arn", _AWS_SYNONYMS)
        if role_arn:
            session = _build_boto3_session(data)
            resolved = session.get_credentials().resolve()
            con.execute(
                f"SET s3_access_key_id='{resolved.access_key}';"
                f"SET s3_secret_access_key='{resolved.secret_key}';"
                f"SET s3_region='{region}';"
            )
            if resolved.token:
                con.execute(f"SET s3_session_token='{resolved.token}';")
        elif access_key and secret_key:
            con.execute(
                f"SET s3_access_key_id='{access_key}';"
                f"SET s3_secret_access_key='{secret_key}';"
                f"SET s3_region='{region}';"
            )
            if session_tok:
                con.execute(f"SET s3_session_token='{session_tok}';")
        try:
            result = con.execute(sql)
            columns = [d[0] for d in result.description]
            rows = [list(r) for r in result.fetchmany(_ROW_LIMIT + 1)]
            return columns, rows
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"S3/DuckDB query error: {e}")
    finally:
        con.close()


def _execute_duckdb_gcs(data: dict, sql: str) -> tuple[list[str], list[list]]:
    import duckdb

    con = duckdb.connect()
    try:
        con.execute(f"SET memory_limit='{_DUCKDB_MEMORY}'; SET threads={_DUCKDB_THREADS};")
        con.execute("INSTALL httpfs; LOAD httpfs;")
        access_key = _pick(data, "access_key", _GCS_SYNONYMS)
        secret_key = _pick(data, "secret_key", _GCS_SYNONYMS)
        endpoint = _pick(data, "endpoint", _GCS_SYNONYMS, "storage.googleapis.com")
        if not access_key or not secret_key:
            raise HTTPException(
                status_code=400,
                detail=f"GCS connection missing HMAC access_key/secret_key. Got keys: {list(data.keys())}",
            )
        con.execute(
            f"SET s3_endpoint='{endpoint}';"
            "SET s3_url_style='path';"
            f"SET s3_access_key_id='{access_key}';"
            f"SET s3_secret_access_key='{secret_key}';"
        )
        try:
            result = con.execute(sql)
            columns = [d[0] for d in result.description]
            rows = [list(r) for r in result.fetchmany(_ROW_LIMIT + 1)]
            return columns, rows
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"GCS/DuckDB query error: {e}")
    finally:
        con.close()


def _execute_duckdb_azure(data: dict, sql: str) -> tuple[list[str], list[list]]:
    import duckdb

    con = duckdb.connect()
    try:
        con.execute(f"SET memory_limit='{_DUCKDB_MEMORY}'; SET threads={_DUCKDB_THREADS};")
        con.execute("INSTALL azure; LOAD azure;")
        conn_str = _pick(data, "connection_string", _AZURE_SYNONYMS)
        account_name = _pick(data, "account_name", _AZURE_SYNONYMS)
        account_key = _pick(data, "account_key", _AZURE_SYNONYMS)
        if conn_str:
            con.execute(f"SET azure_storage_connection_string='{conn_str}';")
        elif account_name and account_key:
            con.execute(
                f"SET azure_account_name='{account_name}';SET azure_account_key='{account_key}';"
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Azure connection missing connection_string or account_name+account_key. Got keys: {list(data.keys())}",
            )
        try:
            result = con.execute(sql)
            columns = [d[0] for d in result.description]
            rows = [list(r) for r in result.fetchmany(_ROW_LIMIT + 1)]
            return columns, rows
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Azure/DuckDB query error: {e}")
    finally:
        con.close()


# ── Driver dispatch map ────────────────────────────────────────────────────────

_DRIVER_MAP = {
    "connection.postgresql": _execute_postgresql,
    "connection.mysql": _execute_mysql,
    "connection.AWS": _execute_aws,  # Athena → Redshift → S3 (DuckDB)
    "connection.gcp": _execute_gcp,  # BigQuery → GCS (DuckDB)
    "connection.azure": _execute_duckdb_azure,  # Azure Blob (DuckDB)
}


# ── Models & endpoint ──────────────────────────────────────────────────────────


class QueryRequest(BaseModel):
    connection_laui: str
    sql: str


class QueryResponse(BaseModel):
    columns: list[str]
    rows: list[list]
    row_count: int
    truncated: bool = False


@query_router.post("/execute", response_model=QueryResponse)
async def execute_query(
    req: QueryRequest,
    orchestrator: ItemOrchestrator = Depends(get_item_orchestrator),
):
    _validate_sql(req.sql)

    try:
        item = await orchestrator.catalog_service.find_item(PydanticObjectId(req.connection_laui))
    except Exception as e:
        raise HTTPException(
            status_code=404, detail=f"Connection item not found or access denied: {e}"
        )

    if not (item.item_type or "").startswith("connection."):
        raise HTTPException(status_code=400, detail="Item is not a connection type.")

    executor = _DRIVER_MAP.get(item.item_type)
    if not executor:
        raise HTTPException(
            status_code=400,
            detail=f"Connection type '{item.item_type}' is not supported for data inspection. "
            f"Supported types: {list(_DRIVER_MAP)}",
        )

    raw = getattr(item, "content", None) or getattr(item, "data", None) or {}
    if isinstance(raw, str):
        raw = json.loads(raw or "{}")
    data: dict = raw if isinstance(raw, dict) else {}

    try:
        columns, rows = await asyncio.wait_for(
            asyncio.to_thread(executor, data, req.sql),
            timeout=120.0,
        )
    except TimeoutError:
        raise HTTPException(status_code=504, detail="Query timed out after 2 minutes.")

    truncated = len(rows) > _ROW_LIMIT
    if truncated:
        rows = rows[:_ROW_LIMIT]

    return QueryResponse(columns=columns, rows=rows, row_count=len(rows), truncated=truncated)
