# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
# Experimental Preview — read-only report embed endpoint.
# BI Embed Token endpoint — Power BI, Looker, QuickSight, Tableau
# Backend exchanges long-lived credentials for a short-lived embed URL.
# Credentials never leave the backend; only the embed URL is returned.
#
# Auth preference (no keys in catalog):
#   QuickSight → connection.AWSIAMRole or connection.AWS with no keys → EC2 instance profile
#   Power BI   → connection.azure with use_managed_identity:true → Azure Managed Identity
#   Looker     → connection.gcp with embed_secret (symmetric, server-side only)
#   Tableau    → connection.tableau with Connected App JWT (HS256, stdlib only)
import base64
import hashlib
import hmac
import json
import os
import time
import urllib.parse
import uuid

_MOCK_URL = os.environ.get("EMBED_MOCK_URL")  # set in .env to skip BI creds during local testing
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from pydantic_mongo import PydanticObjectId

from src.core.catalog.orchestrator import ItemOrchestrator, get_item_orchestrator

embed_router = APIRouter()

_POWERBI_REPORT_TYPES = {"powerbi_report"}
_LOOKER_REPORT_TYPES = {"looker_report"}
_LOOKER_STUDIO_REPORT_TYPES = {"looker_studio_report"}
_QS_REPORT_TYPES = {"quicksight_report"}
_TABLEAU_REPORT_TYPES = {"tableau_report"}
_ALL_EMBED_TYPES = (
    _POWERBI_REPORT_TYPES
    | _LOOKER_REPORT_TYPES
    | _LOOKER_STUDIO_REPORT_TYPES
    | _QS_REPORT_TYPES
    | _TABLEAU_REPORT_TYPES
)

# ── Helpers ────────────────────────────────────────────────────────────────────


def _content(item) -> dict:
    raw = getattr(item, "content", None) or getattr(item, "data", None) or {}
    if isinstance(raw, str):
        raw = json.loads(raw or "{}")
    return raw if isinstance(raw, dict) else {}


def _pick(d: dict, *keys):
    for k in keys:
        if k in d:
            return d[k]
    return None


# ── Power BI ───────────────────────────────────────────────────────────────────


def _embed_powerbi(report_item, conn_data: dict) -> dict:
    try:
        import requests
    except ImportError:
        raise HTTPException(status_code=501, detail="requests not installed.")

    report_id = getattr(report_item, "report_id", None) or ""
    dataset_id = getattr(report_item, "dataset_id", None)
    workspace_id = _pick(conn_data, "workspace_id")
    tenant_id = _pick(conn_data, "tenant_id")
    client_id = _pick(conn_data, "client_id")

    if not report_id or not workspace_id:
        raise HTTPException(
            status_code=400,
            detail="powerbi_report requires report_id; connection.azure requires workspace_id.",
        )

    # Acquire access token
    use_mi = conn_data.get("use_managed_identity", False)
    if use_mi:
        try:
            from azure.identity import ManagedIdentityCredential

            credential = ManagedIdentityCredential(client_id=client_id)
            token = credential.get_token("https://analysis.windows.net/powerbi/api/.default").token
        except ImportError:
            raise HTTPException(status_code=501, detail="azure-identity not installed.")
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Managed Identity auth failed: {e}")
    else:
        client_secret = _pick(conn_data, "client_secret")
        if not tenant_id or not client_id or not client_secret:
            raise HTTPException(
                status_code=400,
                detail="Power BI connection missing tenant_id/client_id/client_secret (or set use_managed_identity:true).",
            )
        token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
        resp = requests.post(
            token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
                "scope": "https://analysis.windows.net/powerbi/api/.default",
            },
            timeout=15,
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail=f"Power BI token error: {resp.text[:200]}")
        token = resp.json()["access_token"]

    # Generate embed token
    body: dict = {
        "accessLevel": "View",
        "reports": [{"id": report_id}],
        "datasets": [{"id": dataset_id}] if dataset_id else [],
    }
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    gen_url = f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/reports/{report_id}/GenerateToken"
    gen_resp = requests.post(gen_url, json=body, headers=headers, timeout=15)
    if gen_resp.status_code != 200:
        raise HTTPException(
            status_code=502, detail=f"Power BI GenerateToken error: {gen_resp.text[:200]}"
        )

    data = gen_resp.json()
    embed_url = f"https://app.powerbi.com/reportEmbed?reportId={report_id}&groupId={workspace_id}"
    expires_in = int(data.get("expiration", 600) or 600)
    return {"embed_url": embed_url, "embed_token": data.get("token"), "expires_in": expires_in}


# ── Looker ─────────────────────────────────────────────────────────────────────


def _embed_looker(report_item, conn_data: dict) -> dict:
    embed_path = getattr(report_item, "embed_path", None) or ""
    host = _pick(conn_data, "host")
    embed_secret = _pick(conn_data, "embed_secret")
    embed_domain = _pick(conn_data, "embed_domain", "")

    if not embed_path or not host or not embed_secret:
        raise HTTPException(
            status_code=400,
            detail="looker_report requires embed_path; connection.gcp requires host and embed_secret.",
        )

    nonce = str(time.time_ns())
    ts = str(int(time.time()))
    params = {"nonce": nonce, "time": ts, "session_length": "300", "external_user_id": "la_embed"}
    if embed_domain:
        params["permissions"] = json.dumps(["access_data", "see_looks", "see_user_dashboards"])
    # Looker SSO: sign only the embed path + params, NOT the /login/embed prefix
    path_to_sign = embed_path + "?" + urllib.parse.urlencode(params)
    sig = hmac.new(embed_secret.encode(), path_to_sign.encode(), hashlib.sha1).hexdigest()
    embed_url = f"https://{host}/login/embed{path_to_sign}&signature={sig}"
    return {"embed_url": embed_url, "expires_in": 300}


# ── QuickSight ─────────────────────────────────────────────────────────────────


def _build_qs_session(conn_data: dict, conn_type: str):
    import boto3

    region = _pick(conn_data, "region", "aws_region") or "us-east-1"
    access_key = _pick(conn_data, "aws_access_key_id", "access_key", "access_key_id")
    secret_key = _pick(conn_data, "aws_secret_access_key", "secret_key", "secret_access_key")
    role_arn = _pick(conn_data, "assume_iam_role", "role_arn", "iam_role")

    # connection.AWSIAMRole or connection.AWS with no keys → instance profile
    if conn_type == "connection.AWSIAMRole" or (not access_key and not secret_key and not role_arn):
        return boto3.Session(region_name=region)
    if role_arn:
        sts = boto3.client("sts", region_name=region)
        creds = sts.assume_role(RoleArn=role_arn, RoleSessionName="la_qs_embed")["Credentials"]
        return boto3.Session(
            aws_access_key_id=creds["AccessKeyId"],
            aws_secret_access_key=creds["SecretAccessKey"],
            aws_session_token=creds["SessionToken"],
            region_name=region,
        )
    return boto3.Session(
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region,
    )


def _embed_quicksight(report_item, conn_data: dict, conn_type: str) -> dict:
    dashboard_id = getattr(report_item, "dashboard_id", None) or ""
    account_id = getattr(report_item, "account_id", None) or _pick(conn_data, "account_id")
    namespace = (
        getattr(report_item, "namespace", None) or _pick(conn_data, "namespace") or "default"
    )
    region = _pick(conn_data, "region", "aws_region") or "us-east-1"

    if not dashboard_id:
        raise HTTPException(status_code=400, detail="quicksight_report requires dashboard_id.")
    if not account_id:
        raise HTTPException(
            status_code=400,
            detail="quicksight_report requires account_id (on the report item or in the connection).",
        )

    import os

    public_url = os.environ.get("PUBLIC_URL", "http://localhost:3000")
    # AllowedDomains expects hostname only, not full URL with protocol
    allowed_domain = urllib.parse.urlparse(public_url).netloc or public_url

    try:
        session = _build_qs_session(conn_data, conn_type)
        client = session.client("quicksight")
        resp = client.generate_embed_url_for_anonymous_user(
            AwsAccountId=account_id,
            Namespace=namespace,
            AuthorizedResourceArns=[
                f"arn:aws:quicksight:{region}:{account_id}:dashboard/{dashboard_id}"
            ],
            ExperienceConfiguration={"Dashboard": {"InitialDashboardId": dashboard_id}},
            AllowedDomains=[allowed_domain],
            SessionLifetimeInMinutes=600,
        )
        return {"embed_url": resp["EmbedUrl"], "expires_in": 36000}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"QuickSight embed error: {e}")


# ── Tableau ────────────────────────────────────────────────────────────────────


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _tableau_jwt(client_id: str, secret_id: str, secret_value: str, embed_user: str) -> str:
    _sep = (",", ":")  # compact JSON — no spaces; some JWT parsers reject whitespace
    header = _b64url(
        json.dumps({"alg": "HS256", "typ": "JWT", "kid": secret_id}, separators=_sep).encode()
    )
    payload = _b64url(
        json.dumps(
            {
                "iss": client_id,
                "exp": int(time.time()) + 600,
                "jti": str(uuid.uuid4()),
                "aud": "tableau",
                "sub": embed_user,
                "scp": ["tableau:views:embed", "tableau:metrics:embed"],
            },
            separators=_sep,
        ).encode()
    )
    signing_input = f"{header}.{payload}"
    sig = _b64url(hmac.new(secret_value.encode(), signing_input.encode(), hashlib.sha256).digest())
    return f"{signing_input}.{sig}"


def _embed_tableau(report_item, conn_data: dict) -> dict:
    view_path = getattr(report_item, "view_path", None) or ""
    embed_user = (
        getattr(report_item, "embed_user", None)
        or _pick(conn_data, "default_embed_user", "embed_user")
        or "guest"
    )
    server_url = (_pick(conn_data, "server_url", "tableau_server", "url") or "").rstrip("/")
    site_id = _pick(conn_data, "site_id", "tableau_site") or ""
    client_id = _pick(conn_data, "client_id") or ""
    secret_id = _pick(conn_data, "secret_id") or ""
    secret_value = _pick(conn_data, "secret_value", "client_secret") or ""

    if not view_path or not server_url:
        raise HTTPException(
            status_code=400,
            detail="tableau_report requires view_path; connection.tableau requires server_url.",
        )
    if not client_id or not secret_id or not secret_value:
        raise HTTPException(
            status_code=400,
            detail="connection.tableau requires client_id, secret_id, and secret_value (Connected App credentials).",
        )

    token = _tableau_jwt(client_id, secret_id, secret_value, embed_user)
    # Multi-site Tableau Cloud uses /t/<site_id>/views/...; default site omits /t/
    if site_id:
        embed_url = f"{server_url}/t/{site_id}/views/{view_path.lstrip('/')}?:embed=yes&:jwtToken={token}&:toolbar=hidden"
    else:
        embed_url = f"{server_url}/views/{view_path.lstrip('/')}?:embed=yes&:jwtToken={token}&:toolbar=hidden"

    return {"embed_url": embed_url, "expires_in": 600}


# ── Route ──────────────────────────────────────────────────────────────────────


class EmbedTokenRequest(BaseModel):
    item_laui: str


class EmbedTokenResponse(BaseModel):
    embed_url: str
    embed_token: str | None = None  # Power BI requires a separate embed token alongside the URL
    expires_in: int


@embed_router.post("/token", response_model=EmbedTokenResponse)
async def get_embed_token(
    req: EmbedTokenRequest,
    orchestrator: ItemOrchestrator = Depends(get_item_orchestrator),
):
    try:
        report_item = await orchestrator.catalog_service.find_item(PydanticObjectId(req.item_laui))
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Report item not found: {e}")

    if report_item.item_type not in _ALL_EMBED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Item type '{report_item.item_type}' is not embeddable. "
            f"Supported: {sorted(_ALL_EMBED_TYPES)}",
        )

    if _MOCK_URL:
        return EmbedTokenResponse(embed_url=_MOCK_URL, expires_in=60)

    # Looker Studio: embed_url is stored directly on the item — no connection needed
    if report_item.item_type in _LOOKER_STUDIO_REPORT_TYPES:
        embed_url = getattr(report_item, "embed_url", None)
        if not embed_url:
            raise HTTPException(
                status_code=400, detail="looker_studio_report requires embed_url on the item."
            )
        return EmbedTokenResponse(embed_url=embed_url, expires_in=86400)

    connection_laui = getattr(report_item, "connection_laui", None)
    if not connection_laui:
        raise HTTPException(status_code=400, detail="Report item missing connection_laui.")

    try:
        conn_oid = (
            connection_laui
            if isinstance(connection_laui, PydanticObjectId)
            else PydanticObjectId(str(connection_laui))
        )
        conn_item = await orchestrator.catalog_service.find_item(conn_oid)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Connection item not found: {e}")

    conn_data = _content(conn_item)
    conn_type = conn_item.item_type or ""

    if report_item.item_type in _POWERBI_REPORT_TYPES:
        if not conn_type.startswith("connection.azure"):
            raise HTTPException(
                status_code=400,
                detail=f"powerbi_report requires connection.azure, got '{conn_type}'.",
            )
        result = _embed_powerbi(report_item, conn_data)

    elif report_item.item_type in _LOOKER_REPORT_TYPES:
        if not conn_type.startswith("connection.gcp"):
            raise HTTPException(
                status_code=400, detail=f"looker_report requires connection.gcp, got '{conn_type}'."
            )
        result = _embed_looker(report_item, conn_data)

    elif report_item.item_type in _QS_REPORT_TYPES:
        if conn_type not in ("connection.AWSIAMRole", "connection.AWS"):
            raise HTTPException(
                status_code=400,
                detail=f"quicksight_report requires connection.AWSIAMRole or connection.AWS, got '{conn_type}'.",
            )
        result = _embed_quicksight(report_item, conn_data, conn_type)

    else:  # tableau_report
        if not conn_type.startswith("connection.tableau"):
            raise HTTPException(
                status_code=400,
                detail=f"tableau_report requires connection.tableau, got '{conn_type}'.",
            )
        result = _embed_tableau(report_item, conn_data)

    return EmbedTokenResponse(**result)
