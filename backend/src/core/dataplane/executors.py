# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
"""In-process data-plane executors shared by the MCP tools and the /query route.

Read-only access to catalog connections:
  - SQL inspection (run_query) across PostgreSQL, MySQL, AWS (Athena/Redshift/S3),
    GCP (BigQuery/GCS) and Azure Blob — extracted from the former query.py route.
  - AWS per-service control-plane reads (aws_read_call) via boto3.
  - GCP per-service control-plane reads (gcp_read_call) via the Discovery API.

All credentials come from the connection item's free-form ``content`` dict, picked
via the synonym maps below. Framework-agnostic: callers translate DataplaneError
(route -> HTTPException, MCP tool -> {"error": ...}).
"""

import json
import re
import time

import psycopg2
from pydantic_mongo import PydanticObjectId

_ROW_LIMIT = 10_000
_DUCKDB_MEMORY = "512MB"  # per-query cap; prevents OOM on large S3/GCS/Azure scans
_DUCKDB_THREADS = 2  # prevent CPU starvation on the shared server


class DataplaneError(Exception):
    """Framework-agnostic error carrying an HTTP-style status code and detail."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


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
        raise DataplaneError(400, "Only SELECT / WITH / EXPLAIN queries are allowed.")
    if ";" in normalized:
        raise DataplaneError(400, "Multiple statements are not permitted i.e ';' is not permitted.")
    for kw in _BLOCKED_KEYWORDS:
        if re.search(rf"\b{kw}\b", normalized):
            raise DataplaneError(400, f"Keyword '{kw.upper()}' is not permitted.")


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
    # service-principal credentials for ARM control-plane / Azure MCP proxy
    "tenant_id": ["tenant_id", "azure_tenant_id", "tenant"],
    "client_id": ["client_id", "azure_client_id", "app_id", "application_id"],
    "client_secret": ["client_secret", "azure_client_secret", "app_secret", "secret"],
    "subscription_id": ["subscription_id", "azure_subscription_id", "subscription"],
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
        raise DataplaneError(
            400, f"PostgreSQL connection missing database/user. Got keys: {list(data.keys())}"
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
        raise DataplaneError(502, f"Cannot connect to PostgreSQL: {e}")
    except psycopg2.Error as e:
        raise DataplaneError(400, f"PostgreSQL query error: {e.pgerror or str(e)}")


def _execute_mysql(data: dict, sql: str) -> tuple[list[str], list[list]]:
    try:
        import pymysql
    except ImportError:
        raise DataplaneError(501, "pymysql not installed — add pymysql to backend dependencies.")
    host = _pick(data, "host", _MYSQL_SYNONYMS, "localhost")
    port = int(_pick(data, "port", _MYSQL_SYNONYMS, 3306))
    database = _pick(data, "database", _MYSQL_SYNONYMS, "")
    user = _pick(data, "user", _MYSQL_SYNONYMS, "")
    password = _pick(data, "password", _MYSQL_SYNONYMS, "")
    charset = _pick(data, "charset", _MYSQL_SYNONYMS, "utf8mb4")
    if not database or not user:
        raise DataplaneError(
            400, f"MySQL connection missing database/user. Got keys: {list(data.keys())}"
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
        raise DataplaneError(502, f"Cannot connect to MySQL: {e}")
    except pymysql.Error as e:
        raise DataplaneError(400, f"MySQL query error: {e}")


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


def _execute_aws(data: dict, sql: str) -> tuple[list[str], list[list]]:
    # Athena/Redshift SQL is served by the awslabs MCP servers (aws_athena /
    # aws_redshift tools), not the in-process SQL path. Only raw S3 file reads
    # (parquet/CSV via DuckDB) run here.
    if _pick(data, "output_location", _AWS_SYNONYMS):
        raise DataplaneError(
            400,
            "Athena SQL is served by the awslabs MCP — use the aws_athena tool instead "
            "of inspect_data / the query editor.",
        )
    if _pick(data, "cluster_identifier", _AWS_SYNONYMS) or _pick(
        data, "workgroup_name", _AWS_SYNONYMS
    ):
        raise DataplaneError(
            400,
            "Redshift SQL is served by the awslabs MCP — use the aws_redshift tool "
            "(execute_query) instead of inspect_data / the query editor.",
        )
    # Plain S3 connection — read files via DuckDB.
    return _execute_duckdb_s3(data, sql)


def _execute_bigquery(data: dict, sql: str) -> tuple[list[str], list[list]]:
    try:
        from google.cloud import bigquery
        from google.oauth2 import service_account
    except ImportError:
        raise DataplaneError(501, "google-cloud-bigquery not installed.")
    project = _pick(data, "project", _BQ_SYNONYMS)
    creds_raw = _pick(data, "credentials", _BQ_SYNONYMS)
    location = _pick(data, "location", _BQ_SYNONYMS, "US")
    if not project:
        raise DataplaneError(
            400, f"BigQuery connection missing project. Got keys: {list(data.keys())}"
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
    except DataplaneError:
        raise
    except Exception as e:
        raise DataplaneError(502, f"BigQuery error: {e}")


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
            raise DataplaneError(400, f"S3/DuckDB query error: {e}")
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
            raise DataplaneError(
                400,
                f"GCS connection missing HMAC access_key/secret_key. Got keys: {list(data.keys())}",
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
        except DataplaneError:
            raise
        except Exception as e:
            raise DataplaneError(400, f"GCS/DuckDB query error: {e}")
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
            raise DataplaneError(
                400,
                f"Azure connection missing connection_string or account_name+account_key. Got keys: {list(data.keys())}",
            )
        try:
            result = con.execute(sql)
            columns = [d[0] for d in result.description]
            rows = [list(r) for r in result.fetchmany(_ROW_LIMIT + 1)]
            return columns, rows
        except DataplaneError:
            raise
        except Exception as e:
            raise DataplaneError(400, f"Azure/DuckDB query error: {e}")
    finally:
        con.close()


# ── Driver dispatch map ────────────────────────────────────────────────────────

_DRIVER_MAP = {
    "connection.postgresql": _execute_postgresql,
    "connection.mysql": _execute_mysql,
    "connection.AWS": _execute_aws,  # S3 file reads (DuckDB); Athena/Redshift via awslabs MCP
    "connection.gcp": _execute_gcp,  # BigQuery → GCS (DuckDB)
    "connection.azure": _execute_duckdb_azure,  # Azure Blob (DuckDB)
}


# ── Connection resolution & SQL entrypoint ──────────────────────────────────────


async def resolve_connection(orchestrator, connection_laui: str) -> tuple[str, dict]:
    """Resolve a connection item to (item_type, content_dict).

    Runs through the catalog service, which enforces per-user access via the
    current user context — so callers must run inside an established user_context
    (the auth middleware sets it for both API and /mcp requests).
    """
    try:
        item = await orchestrator.catalog_service.find_item(PydanticObjectId(connection_laui))
    except Exception as e:
        raise DataplaneError(404, f"Connection item not found or access denied: {e}")

    item_type = item.item_type or ""
    if not item_type.startswith("connection."):
        raise DataplaneError(400, "Item is not a connection type.")

    raw = getattr(item, "content", None) or getattr(item, "data", None) or {}
    if isinstance(raw, str):
        raw = json.loads(raw or "{}")
    data: dict = raw if isinstance(raw, dict) else {}
    return item_type, data


def run_query(item_type: str, data: dict, sql: str) -> tuple[list[str], list[list]]:
    """Validate SQL and execute it against the connection. Synchronous — callers
    should wrap with asyncio.to_thread under a timeout."""
    _validate_sql(sql)
    executor = _DRIVER_MAP.get(item_type)
    if not executor:
        raise DataplaneError(
            400,
            f"Connection type '{item_type}' is not supported for data inspection. "
            f"Supported types: {list(_DRIVER_MAP)}",
        )
    return executor(data, sql)


def _json_safe(obj):
    return json.loads(json.dumps(obj, default=str))


# ── GCP per-service control-plane reads (Discovery API) ──────────────────────────

# tool name → (discovery api, version). BigQuery data still goes through inspect_data SQL.
GCP_SERVICE_TOOLS: dict[str, tuple[str, str]] = {
    "gcp_storage": ("storage", "v1"),
    "gcp_bigquery": ("bigquery", "v2"),
    "gcp_compute": ("compute", "v1"),
    "gcp_logging": ("logging", "v2"),
    "gcp_monitoring": ("monitoring", "v3"),
    "gcp_iam": ("iam", "v1"),
    "gcp_resourcemanager": ("cloudresourcemanager", "v3"),
    "gcp_pubsub": ("pubsub", "v1"),
}

_GCP_READ_METHODS = {
    "list",
    "get",
    "aggregatedList",
    "search",
    "getIamPolicy",
    "testIamPermissions",
    "query",
    "read",
}


def _gcp_credentials(data: dict):
    from google.oauth2 import service_account

    creds_raw = _pick(data, "credentials", _BQ_SYNONYMS)
    if not creds_raw:
        raise DataplaneError(
            400,
            f"GCP connection missing service-account credentials. Got keys: {list(data.keys())}",
        )
    info = creds_raw if isinstance(creds_raw, dict) else json.loads(creds_raw)
    return service_account.Credentials.from_service_account_info(
        info, scopes=["https://www.googleapis.com/auth/cloud-platform.read-only"]
    )


def gcp_read_call(
    data: dict,
    api: str,
    version: str,
    method: str,
    parameters: dict | None,
    resource_path: str | None = None,
) -> dict:
    """Execute a read-only Google Cloud Discovery API call.

    resource_path navigates nested resources, e.g. "instances" for compute, or
    "projects.locations.buckets" — dotted. ``method`` is the final read verb.
    """
    leaf = (method or "").split(".")[-1]
    if leaf not in _GCP_READ_METHODS:
        raise DataplaneError(
            400,
            f"Method '{method}' is not a read-only method. Allowed: {sorted(_GCP_READ_METHODS)}.",
        )
    try:
        from googleapiclient.discovery import build
    except ImportError:
        raise DataplaneError(501, "google-api-python-client not installed.")
    try:
        creds = _gcp_credentials(data)
        service = build(api, version, credentials=creds, cache_discovery=False)
    except DataplaneError:
        raise
    except Exception as e:
        raise DataplaneError(502, f"Cannot build GCP client for '{api}/{version}': {e}")

    # Walk the resource chain (e.g. "instances" or "projects.locations") then call method.
    target = service
    try:
        for part in (resource_path or "").split("."):
            if not part:
                continue
            target = getattr(target, part)()
        request = getattr(target, leaf)(**(parameters or {}))
        resp = request.execute()
    except DataplaneError:
        raise
    except Exception as e:
        raise DataplaneError(400, f"GCP {api}.{resource_path or ''}.{leaf} error: {e}")
    return _json_safe(resp)
