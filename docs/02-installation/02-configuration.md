# Configuration

Two layers of configuration: **deployment** (env / `deploy/.env`) and **platform** (`config/system.yml`). Secrets are referenced, never stored in plain text.

## Deployment configuration — `deploy/.env`

Copy `deploy/.env.example` → `deploy/.env` to override defaults. Common knobs:

| Knob | Purpose |
|---|---|
| image repo / tags | which images to pull (`leastactionlabs/leastaction`) |
| root login | initial admin email / username / password |
| public URL | external base URL |
| `LEASTACTION_HTTP_PORT` | host port for the edge frontend (default 8080) |
| drain / health timeouts | `LEASTACTION_DRAIN_TIMEOUT`, `LEASTACTION_DRAIN_HARD_KILL`, health-check timeouts |
| flower | enable the Celery Flower dashboard (profile-gated) |

Everything works with no `.env` at all. See `deploy/.env.example` for the full list.

## Platform configuration — `config/system.yml`

`system.yml` is the infrastructure config (not part of the user-facing parameter config hierarchy). It controls:

- **Operator ↔ connection mappings** and whether they're enforced — `enforce_connection_operator_mapping: true` validates operator/connection subtype pairs at task creation.
- **Worker settings** and **scheduler** behavior.

> The user-facing **config hierarchy** (System → Workflow → Task parameters, retries, SLA, defaults) is a different thing — see the [Config concept](/path?laui=getting-started-04-concepts-05-config&itemtype=doc.file&itemname=Config).

## Secrets

Never store plain-text credentials in a connection. Reference a secret with a placeholder, resolved at runtime:

```json
{
  "host": "db.example.com",
  "user": "pipeline_user",
  "password": "${AWS_SECRET_MANAGER:db-password}"
}
```

Supported placeholders include AWS Secrets Manager and environment variables (and others — see the [Connection concept](/path?laui=getting-started-04-concepts-02-connection&itemtype=doc.file&itemname=Connection)). The resolved value never leaves the server.

## AI providers

The AI generation layer is itself a catalog `chat`/`agent` item pointing at a `connection` that holds your provider API key and model — no provider is hard-coded. See [AI overview](/path?laui=getting-started-06-ai-01-overview&itemtype=doc.file&itemname=Overview).

## Next
- [Production (Blue-Green)](/path?laui=getting-started-02-installation-03-production-blue-green&itemtype=doc.file&itemname=Production%20Blue%20Green) — zero-downtime deploys.
