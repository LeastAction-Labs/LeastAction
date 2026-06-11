<operator/action/doc pending>

You are an AI data engineer. Let's build an end-to-end Airflow DAG management skill for LeastAction — an enterprise-grade, high-level AI orchestration system that lets teams manage any number of jobs on any system without requiring provider updates.

This skill covers three parts:
1. **Action** — Import DAGs from Git into LeastAction as tasks (with or without embedding the DAG code)
2. **Operator** — Run and manage Airflow DAGs via the Airflow REST API, with LeastAction parameters driving execution
3. **User Guide** — Blog-style documentation with real examples showing the Git → LeastAction → Airflow lifecycle

---

## Context

### How the skill fits into LeastAction

LeastAction is the control plane. Airflow is the execution target. This skill bridges them:
- A user imports a DAG definition from Git into LeastAction as a task (via action)
- LeastAction schedules and manages that task like any other
- At run time, the operator triggers the DAG in Airflow using the Airflow REST API
- If `with_code` mode: the DAG source flows Git → LeastAction → Airflow at run time (no stale code in Airflow)
- If without code (reference mode): the DAG already exists in Airflow; LeastAction just triggers it by name

### Import action — two modes

**With code (`with_code: true`)**
- The action fetches the DAG file from Git at import time and embeds it as the task payload
- At run time, the operator uploads the DAG code to Airflow (via Airflow's Files/DAGs API or shared storage) before triggering
- The code source of truth is Git → LeastAction catalog → Airflow (runtime). Airflow never stores stale versions
- Payload at task creation: the actual Python DAG code (string)

**Without code (`with_code: false`)**
- The action creates the task in LeastAction with only a reference — dag_id and optionally a path
- The DAG must already be deployed to Airflow by another process
- LeastAction's job is scheduling, parameterization, and triggering — not code delivery
- Payload at task creation: `{"dag_id": "my_dag", "description": "..."}`

### Operator behavior

- Connects to Airflow via REST API (base_url, username, password in connection)
- `logical_date` and `config` are LeastAction task parameters — they map directly to Airflow's `logical_date` (execution_date) and `conf` in the DAG trigger payload
- When `with_code` mode (detected from payload type or a flag): uploads the DAG code to Airflow before triggering, waits for Airflow to parse it, then triggers
- Triggers the DAG run via POST /api/v1/dags/{dag_id}/dagRuns
- Polls DAG run state via GET /api/v1/dags/{dag_id}/dagRuns/{dag_run_id} until terminal state
- Returns run details (dag_run_id, state, start_date, end_date)

### Key LeastAction concepts to use

- `least_action_task_object.get('logical_date')` — the task's scheduled logical date, passed as Airflow execution_date
- `least_action_task_object.get('config', {})` — merged config parameters, passed as Airflow DAG `conf`
- `least_action_task_object.get('payload')` — either DAG source code string (with_code) or JSON reference (without code)
- `least_action_task_object.get('connection')` — Airflow credentials: `base_url`, `username`, `password`
- `least_action_task_object.get('name')` — task name, useful for logging and dag_id derivation
- LeastAction config parameters (`{{logical_date}}`, `{{dag_id}}`, `{{airflow_pool}}`, etc.) are resolved before the operator runs
- Parameters doc: LeastAction/frontend/docs/advanced/config.md

### Reference files
- Action system prompt: LeastAction/config/AI/action.txt
- Operator system prompt: LeastAction/config/AI/operator.txt
- Payload system prompt: LeastAction/config/AI/payload.txt
- Example action (agent pattern): LeastAction/backend/bootstrap/ideas/AggReporting/AggReportingAction/PostgresqlToClaudeChatToHtmlReportToAsset.py
- GitToTask reference: LeastAction/backend/bootstrap/ideas/done/GitToTask/ — how to fetch from Git inside an action
- Action config docs: LeastAction/frontend/docs/advanced/action.md
- Config/parameters docs: LeastAction/frontend/docs/advanced/config.md
- Notify pattern doc: LeastAction/frontend/docs/examples/notify_and_manage/notify-and-manage-pipelines.md
- Running actions doc: LeastAction/frontend/docs/examples/ — reference for chaining pattern

---

## What to build

### 1. Action — `AirflowImportDAGFromGit`

**Purpose:** Import an Airflow DAG from a Git repository into LeastAction as a task.

**run() parameters:**
- `git_repo_url` — Git repo HTTPS URL
- `git_branch` — branch to pull from
- `dag_file_path` — path to the DAG file within the repo (e.g. `dags/my_pipeline.py`)
- `dag_id` — Airflow DAG ID (used as task payload reference and for triggering)
- `workflow_folder_laui` — LeastAction workflow folder where the task will be created
- `with_code` (bool) — if True, embed DAG source code in task payload; if False, store only `{"dag_id": dag_id}`
- `operator_laui` — the Airflow operator to assign to the created task
- `connection_laui` — the Airflow connection laui to assign to the created task
- `logical_date` (optional) — override start date for the created task
- `frequency` (optional) — cron or ADHOC for the created task

**Behavior:**
- Clone or fetch single file from Git using the git connection credentials
- If `with_code=True`: read DAG file content, set as task payload (Python string)
- If `with_code=False`: set payload as `{"dag_id": "<dag_id>"}`
- Create the task in LeastAction via the catalog API with the operator and connection assigned
- Log each step: git fetch, payload preparation, task creation
- Return True on success, False on failure

**connection fields:** `git_token` or `git_username`/`git_password` for private repos (same pattern as LeastActionGitToTask)

**action_variables:** `git_repo_url`, `git_branch`, `dag_file_path`, `dag_id`, `workflow_folder_laui`, `with_code`, `operator_laui`, `connection_laui`, `frequency`

---

### 2. Operator — `AirflowDAGOperator`

**Purpose:** Trigger and monitor an Airflow DAG run via the Airflow REST API. Supports both reference mode and with-code mode.

**4 required methods** (per operator.txt contract):

**initialize(least_action_task_object)**
- Extract connection: `base_url`, `username`, `password`
- Create a requests.Session with BasicAuth and base headers
- Verify connectivity: GET /api/v1/health or /api/v1/version
- Return session client

**run(least_action_task_object, client)**
- Parse payload: if payload is a Python string (contains `def ` or `import `) → with_code mode; if JSON/dict → reference mode
- Extract `dag_id` from payload (reference mode) or from config parameter `dag_id` (with_code mode)
- If with_code mode:
  - Upload DAG code to Airflow: write to Airflow's DAGs folder via Files API or a shared volume path in connection
  - Wait for Airflow to parse the DAG: poll GET /api/v1/dags/{dag_id} until dag is importable (max N retries)
  - Unpause the DAG if paused: PATCH /api/v1/dags/{dag_id} `{"is_paused": false}`
- Build trigger payload:
  - `logical_date` from `least_action_task_object.get('logical_date')` — map to Airflow `logical_date` (ISO format)
  - `conf` from `least_action_task_object.get('config', {}).get('parameters', {})` — pass user config as DAG conf
- Trigger DAG run: POST /api/v1/dags/{dag_id}/dagRuns
- Return `{'dag_run_id': ..., 'dag_id': ..., 'execution_type': 'async', 'status': 'running'}`

**check_completion(least_action_task_object, client, run_details)**
- GET /api/v1/dags/{dag_id}/dagRuns/{dag_run_id}
- Map Airflow states to LeastAction states: `success` → `success`, `failed`/`upstream_failed` → `failed`, `running`/`queued` → `pending`
- Return `{'status': ..., 'message': ..., 'output': {...run details...}}`

**finish(least_action_task_object, client, completion_details, run_details)**
- Log final state and duration
- Close session
- On failure: optionally log Airflow task instance details for debugging

**connection fields:** `base_url` (e.g. `http://airflow.internal:8080`), `username`, `password`

**payload (with_code mode):** Python DAG source code string
**payload (reference mode):** `{"dag_id": "my_dag_id"}`

**config parameters used at runtime:**
- `{{dag_id}}` — override dag_id if not in payload
- `{{airflow_pool}}` — optional pool to pass in conf
- `{{logical_date}}` — auto-populated from LeastAction task scheduling
- Any other key in config.parameters is forwarded to Airflow DAG `conf`

---

### 3. User Guide

**Title:** "Git to Airflow in One Click: Managing DAGs as Code with LeastAction"

**Target audience:** AI data engineer / platform engineer managing Airflow at scale, building for a leadership audience

**Output folder:** `LeastAction/frontend/docs/examples/` — create a new folder `airflow_dag_management/`

**Content to cover:**

1. **The problem** — DAGs scattered across repos, Airflow UI manual triggers, no audit trail, no enterprise scheduling layer, no dependency management across pipelines on different systems

2. **The LeastAction approach** — Git is the source of truth. LeastAction is the control plane. Airflow is one of many execution targets. The same scheduling, dependency, SLA, and action patterns that work for SQL tasks or Python tasks work for Airflow DAGs — without changing Airflow.

3. **Setup** — what you need: Airflow with REST API enabled, a Git repo with DAG files, connections configured in LeastAction (git + airflow)

4. **Sample Git repo structure** — show a reference structure:
```
airflow-dags/
  dags/
    daily_sales_pipeline.py
    hourly_metrics_refresh.py
    customer_segmentation.py
  README.md
```

5. **Importing DAGs — two workflows:**
   - **With code**: user clicks `AirflowImportDAGFromGit` UI action → action fetches DAG from Git → creates LeastAction task with code embedded → at run time operator pushes code to Airflow and triggers. Best for: DAGs that change often, teams that want full code-as-data traceability.
   - **Reference only**: same action with `with_code: false` → creates task with dag_id reference only → operator just triggers. Best for: stable DAGs already managed by a separate CI/CD process.

6. **Running DAGs with LeastAction parameters** — show how `logical_date` and config parameters flow:
   ```json
   {
     "parameters": {
       "dag_id": "daily_sales_pipeline",
       "target_schema": "analytics_prod",
       "batch_size": "1000"
     }
   }
   ```
   These become the DAG `conf` — the DAG reads them with `dag_run.conf.get('target_schema')`. The `logical_date` is the LeastAction task's scheduled date, giving exact backfill control.

7. **Backfilling Airflow DAGs at scale** — set logical_date at import time or use LeastAction reschedule. Same 1-click backfill pattern from the managing_at_scale guide applies here.

8. **Dependencies across systems** — show a task chain: SQL transform completes → Airflow DAG runs with that date's data → downstream report task runs. LeastAction manages the dependency; Airflow handles only its execution segment.

9. **Notifications and SLA** — attach `LeastActionSlackNotify` as a postAction on the Airflow task — same as any other LeastAction task. No Airflow callback configuration needed.

10. **Sample walkthrough** — step-by-step: configure connections → attach config to workflow → use UI action to import → task appears in workflow → scheduled run triggers DAG → monitor in LeastAction task view

11. **Test before use note** — since triggering Airflow DAGs has real side effects (data writes, API calls), test with a safe dummy DAG first. Keep all code in Git to restore quickly.

12. **Comparison note** — contrast with triggering Airflow directly: no enterprise scheduling, no cross-system dependency, no backfill control, no action hooks, no catalog traceability. With LeastAction, Airflow is just another operator — the same abstractions apply everywhere.

Reference existing examples:
- `LeastAction/frontend/docs/examples/notify_and_manage/notify-and-manage-pipelines.md` — for action hooks pattern
- `LeastAction/frontend/docs/examples/managing_at_scale/` — for backfill and dependency patterns

---

## Output options (choose one or both)

**code:**
- Location: `LeastAction/backend/bootstrap/ideas/done/AirflowDAGManagement/`
- Files:
  - `AirflowImportDAGFromGit.py` — action code
  - `AirflowImportDAGFromGit.connection` — connection fields JSON
  - `AirflowImportDAGFromGit.action_variables` — variables JSON
  - `AirflowImportDAGFromGit.sh` — pip dependencies
  - `AirflowDAGOperator.py` — operator code
  - `AirflowDAGOperator.connection` — connection fields JSON
  - `AirflowDAGOperator_withcode.payload` — sample payload (DAG source string)
  - `AirflowDAGOperator_reference.payload` — sample payload (dag_id reference JSON)
  - `AirflowDAGOperator.sh` — pip dependencies
  - Copy this skill file into the folder as a header comment reference

**doc:**
- Location: `LeastAction/frontend/docs/examples/airflow_dag_management/`
- Files: `git-to-airflow-with-leastaction.md`
- Format: markdown, blog-style title, no external links (React handles routing)
- Don't add info to other links — final rendering is done by React

---

## Notes

- Do not add unnecessary comments or parameters
- No defaults unless explicitly needed for Airflow API compatibility
- All code in English and Python only
- The action and operator are just examples of what is possible — users can extend, fork, or replace them entirely
- Mention: keep all custom actions and operators in Git for quick restore and version control
- LeastAction is an enterprise high-level AI management system — frame the guide for a leadership-level data platform audience, not just Airflow admins
