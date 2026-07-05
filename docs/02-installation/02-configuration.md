# Configuration

Two layers of configuration: **deployment** (env / `deploy/.env`) and **platform** (`config/system.yml`). Platform-level secrets come from the environment (optionally AWS Secrets Manager); connection credentials are handled per-operator.

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

There are two separate concerns:

**Platform secrets** (root password, the LLM/Claude API key, infra credentials) resolve through
`backend/src/common/secrets.py:get_secret()` — environment first, then AWS Secrets Manager when
`USE_AWS_SECRETS=true` (with `AWS_SECRETS_NAME` / `AWS_REGION`). Set these in `deploy/.env` or the
environment; they are read at startup and never sent to the browser.

**Connection credentials** are **not** templated. LeastAction passes connection field values to the
operator exactly as stored — it does **not** expand `${...}` placeholders. So secret handling depends
on the operator: prefer IAM roles / managed identities (no credential in the connection), or an
operator that accepts a cloud-native secret reference (e.g. `AWSRedshiftDataExecuteSQL`'s `secret_arn`,
resolved by the AWS SDK). For operators that read fields directly (e.g. `PostgresqlExecuteSQL`), store
the real value and protect the connection with catalog permissions. Full detail in the
[Connection concept → How secrets actually work](/path?laui=getting-started-04-concepts-02-connection&itemtype=doc.file&itemname=Connection).

## AI providers

The AI generation layer is itself a catalog `chat`/`agent` item pointing at a `connection` that holds your provider API key and model — no provider is hard-coded. See [AI overview](/path?laui=getting-started-06-ai-01-overview&itemtype=doc.file&itemname=Overview).

## Next
- [Production (Blue-Green)](/path?laui=getting-started-02-installation-03-production-blue-green&itemtype=doc.file&itemname=Production%20Blue%20Green) — zero-downtime deploys.
