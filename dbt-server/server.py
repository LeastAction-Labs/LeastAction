import subprocess
import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler

DBT_PROJECT_DIR = os.environ.get("DBT_PROJECT_DIR", "/dbt/demo_project")
PORT = int(os.environ.get("PORT", "8001"))


def _dbt_cmd(args):
    return subprocess.run(
        ["dbt"] + args + ["--project-dir", DBT_PROJECT_DIR, "--profiles-dir", DBT_PROJECT_DIR],
        capture_output=True,
        text=True,
        timeout=300,
    )


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self._json_response(200, {"status": "ok"})
        elif self.path == "/list-models":
            self._handle_list_models()
        elif self.path == "/list-models-detail":
            self._handle_list_models_detail()
        else:
            self._json_response(404, {"error": "not found"})

    def do_POST(self):
        if self.path == "/run-model":
            self._handle_run_model()
        elif self.path == "/run-seed":
            self._handle_run_seed()
        elif self.path == "/run-select":
            self._handle_run_select()
        else:
            self._json_response(404, {"error": "not found"})

    def _handle_list_models(self):
        models_dir = os.path.join(DBT_PROJECT_DIR, "models")
        models = [f[:-4] for f in os.listdir(models_dir) if f.endswith(".sql")]
        self._json_response(200, {"models": sorted(models)})

    def _handle_list_models_detail(self):
        models_dir = os.path.join(DBT_PROJECT_DIR, "models")
        models = []
        for f in sorted(os.listdir(models_dir)):
            if f.endswith(".sql"):
                path = os.path.join(models_dir, f)
                with open(path) as fh:
                    content = fh.read()
                refs = []
                import re
                for m in re.finditer(r"\{\{\s*ref\s*\(\s*['\"]([^'\"]+)['\"]\s*\)\s*\}\}", content):
                    refs.append(m.group(1))
                models.append({"name": f[:-4], "refs": refs})
        self._json_response(200, {"models": models})

    def _handle_run_model(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length)) if length else {}
            model = body.get("model", "").strip()
            if not model:
                self._json_response(400, {"error": "missing 'model' field"})
                return
            if model == "seed":
                result = _dbt_cmd(["seed"])
            else:
                result = _dbt_cmd(["run", "--select", model])
            self._json_response(200, {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            })
        except subprocess.TimeoutExpired:
            self._json_response(504, {"error": "dbt run timed out", "success": False})
        except Exception as e:
            self._json_response(500, {"error": str(e), "success": False})

    def _handle_run_seed(self):
        try:
            result = _dbt_cmd(["seed"])
            self._json_response(200, {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            })
        except subprocess.TimeoutExpired:
            self._json_response(504, {"error": "dbt seed timed out", "success": False})
        except Exception as e:
            self._json_response(500, {"error": str(e), "success": False})

    def _handle_run_select(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length)) if length else {}
            model = body.get("model", "").strip()
            if not model:
                self._json_response(400, {"error": "missing 'model' field"})
                return
            result = _dbt_cmd(["run", "--select", model])
            self._json_response(200, {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            })
        except subprocess.TimeoutExpired:
            self._json_response(504, {"error": "dbt run timed out", "success": False})
        except Exception as e:
            self._json_response(500, {"error": str(e), "success": False})

    def _json_response(self, status, body):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())

    def log_message(self, format, *args):
        print(f"[dbt-server] {args[0]}")


if __name__ == "__main__":
    print(f"[dbt-server] Starting on port {PORT}, project dir: {DBT_PROJECT_DIR}")
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
