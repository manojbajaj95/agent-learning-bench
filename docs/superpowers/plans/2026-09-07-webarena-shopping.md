# WebArena Shopping Benchmark Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the mock `tasks/web-exploration` task with a Harbor multi-step benchmark over all 187 WebArena-Verified Shopping-only tasks.

**Architecture:** Run the official Shopping service and reset controller outside Harbor. Inside each Harbor step, a small runtime resets Shopping, starts an isolated authenticated `agent-browser` session with HAR capture, publishes one official task, and evaluates the result with WebArena-Verified. Harbor retains agent learning state and supplies token, cost, and timing metrics.

**Tech Stack:** Harbor task schema 1.4, Python 3.12 stdlib, WebArena-Verified 1.2.3, `agent-browser` 0.36.0, Chromium, Docker.

## Global Constraints

- Work only on `feat/webarena-shopping` in the isolated worktree.
- Pin WebArena-Verified to tag `v1.2.3`, commit `6473f72db5dcefc97b5725b59e734504edc28a21`.
- Include exactly the 187 tasks whose `sites` value is exactly `["shopping"]`.
- Preserve official task IDs, order, intent, start URLs, and evaluator definitions.
- Reset Shopping before every task; never reset `/app/notes.md`, `/app/sessions`, or Harbor trajectory state.
- Load authentication before the measured task; never put username or password in the agent prompt.
- Use upstream `agent-browser` and its bundled skill directly; do not create another browser abstraction.
- Use WebArena-Verified for correctness; do not create another judge or copy expected answers into agent-visible files.
- Reuse Harbor tokens, model cost, and timing. Add only unique URLs and `agent-browser` command count.
- Infrastructure failures must fail the step explicitly, not masquerade as agent reward zero.
- Do not install host-level Docker or Harbor. Document exact prerequisites.
- Do not add a wrapper that launches all three paid conditions.

---

## File Structure

Files retained or replaced under `tasks/web-exploration`:

```text
tasks/web-exploration/
├── README.md                       setup and three run commands
├── download.sh                     fetch pinned official dataset
├── generate_steps.py               filter and generate 187 Harbor steps
├── instruction.md                  static Pi task instructions
├── test_generate_steps.py          dataset and generator checks
├── data/                            downloaded; gitignored
│   ├── webarena-verified.json
│   ├── agent-input.json
│   └── auth.json
├── environment/
│   ├── Dockerfile
│   └── webarena/
│       ├── runtime.py              reset, HAR, evaluation, metrics
│       └── test_runtime.py
└── steps/                           generated; gitignored
```

Delete the obsolete mock files:

```text
tasks/web-exploration/questions.json
tasks/web-exploration/environment/web/pages.py
tasks/web-exploration/environment/web/web.py
tasks/web-exploration/tests/
```

---

### Task 1: Pinned Shopping Dataset and Generator

**Files:**
- Create: `tasks/web-exploration/download.sh`
- Modify: `tasks/web-exploration/generate_steps.py`
- Create: `tasks/web-exploration/test_generate_steps.py`
- Delete: `tasks/web-exploration/questions.json`

**Interfaces:**
- Consumes: official `webarena-verified.json` from pinned commit.
- Produces: `load_shopping_tasks(path: Path) -> list[dict]`.
- Produces: `generate(tasks: list[dict], root: Path, limit: int | None) -> None`.
- Produces: `data/agent-input.json`, `steps/task-XXXX/`, and `task.toml`.

- [ ] **Step 1: Write generator tests**

Use `unittest` and temporary directories; no new test dependency:

```python
class GeneratorTests(unittest.TestCase):
    def test_filters_exact_shopping_only(self):
        rows = [
            {"task_id": 2, "sites": ["shopping"], "intent": "b", "start_urls": ["__SHOPPING__"], "eval": []},
            {"task_id": 1, "sites": ["shopping", "reddit"], "intent": "x", "start_urls": [], "eval": []},
            {"task_id": 3, "sites": ["shopping"], "intent": "c", "start_urls": ["__SHOPPING__"], "eval": []},
        ]
        path = self.write_json(rows)
        self.assertEqual([2, 3], [row["task_id"] for row in load_shopping_tasks(path)])

    def test_rejects_duplicate_task_ids(self):
        rows = [
            {"task_id": 2, "sites": ["shopping"], "intent": "a", "start_urls": ["__SHOPPING__"], "eval": []},
            {"task_id": 2, "sites": ["shopping"], "intent": "b", "start_urls": ["__SHOPPING__"], "eval": []},
        ]
        with self.assertRaisesRegex(ValueError, "duplicate task_id 2"):
            load_shopping_tasks(self.write_json(rows))
```

- [ ] **Step 2: Run tests and confirm the old generator fails them**

Run:

```bash
python3 -m unittest tasks.web-exploration.test_generate_steps -v
```

Expected: import or assertion failure because `load_shopping_tasks` does not exist.

- [ ] **Step 3: Add the pinned downloader**

`download.sh` must use only `curl`, `python3`, and the pinned commit:

```bash
#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$root/data"
url="https://raw.githubusercontent.com/ServiceNow/webarena-verified/6473f72db5dcefc97b5725b59e734504edc28a21/assets/dataset/webarena-verified.json"
curl --fail --location --retry 3 "$url" -o "$root/data/webarena-verified.json"
python3 "$root/generate_steps.py" --check
```

- [ ] **Step 4: Replace the generator minimally**

Implement:

```python
def load_shopping_tasks(path: Path) -> list[dict]:
    rows = json.loads(path.read_text())
    tasks = [row for row in rows if row.get("sites") == ["shopping"]]
    seen: set[int] = set()
    for task in tasks:
        task_id = int(task["task_id"])
        if task_id in seen:
            raise ValueError(f"duplicate task_id {task_id}")
        if not task.get("intent") or not task.get("start_urls"):
            raise ValueError(f"task {task_id} is missing agent input")
        seen.add(task_id)
    return tasks
```

`--check` must assert exactly 187 tasks. `--n N` may generate a smoke subset; default generates all 187. Write only agent-visible fields to `data/agent-input.json`:

```python
{
    "task_id": task["task_id"],
    "intent_template_id": task["intent_template_id"],
    "sites": task["sites"],
    "start_urls": task["start_urls"],
    "intent": task["intent"],
}
```

Keep the full downloaded dataset only in `data/webarena-verified.json`; copy it into the image under `/opt/webarena`, never `/app`.

- [ ] **Step 5: Run unit and pinned-dataset checks**

Run:

```bash
python3 -m unittest tasks.web-exploration.test_generate_steps -v
./tasks/web-exploration/download.sh
python3 tasks/web-exploration/generate_steps.py --check
python3 tasks/web-exploration/generate_steps.py --n 3
```

Expected: unit tests pass; check prints `187 shopping-only tasks`; smoke generation prints `wrote 3 steps`.

- [ ] **Step 6: Commit**

```bash
git add tasks/web-exploration/download.sh tasks/web-exploration/generate_steps.py \
  tasks/web-exploration/test_generate_steps.py tasks/web-exploration/questions.json
git commit -m "feat: generate WebArena shopping steps"
```

---

### Task 2: Runtime Reset and Browser Lifecycle

**Files:**
- Create: `tasks/web-exploration/environment/webarena/runtime.py`
- Create: `tasks/web-exploration/environment/webarena/test_runtime.py`
- Delete: `tasks/web-exploration/environment/web/pages.py`
- Delete: `tasks/web-exploration/environment/web/web.py`

**Interfaces:**
- Consumes environment variables `WEBARENA_SHOPPING_URL`, `WEBARENA_CONTROL_URL`, `WEBARENA_AUTH_STATE`.
- Produces CLI commands `prepare TASK_ID`, `capture-stop`, and `evaluate TASK_ID`.
- Produces `/app/task.json`, `/logs/agent/network.har`, and `/logs/verifier/reward.json`.

- [ ] **Step 1: Write reset and metrics tests**

Mock `urllib.request.urlopen` and `subprocess.run`:

```python
class RuntimeTests(unittest.TestCase):
    def test_prepare_resets_before_starting_har(self):
        with mock.patch.object(runtime, "reset_site") as reset, \
             mock.patch.object(runtime, "browser") as browser:
            runtime.prepare(21, task={"task_id": 21, "intent": "Find item", "start_urls": ["http://shop/"]})
        reset.assert_called_once_with()
        self.assertEqual(
            [mock.call(["close"], check=False), mock.call(["open"]),
             mock.call(["state", "load", runtime.AUTH_STATE]),
             mock.call(["network", "har", "start", "--content", "text"])],
            browser.call_args_list,
        )

    def test_har_metrics_count_unique_shopping_urls(self):
        har = {"log": {"entries": [
            {"request": {"url": "http://shop/a"}},
            {"request": {"url": "http://shop/a"}},
            {"request": {"url": "http://other/b"}},
            {"request": {"url": "http://shop/c"}},
        ]}}
        self.assertEqual({"unique_urls": 2.0}, runtime.har_metrics(har, "http://shop"))

    def test_reset_failure_is_not_reward_zero(self):
        with self.assertRaisesRegex(RuntimeError, "Shopping reset failed"):
            runtime.require_http_ok("http://control/reset", method="POST", opener=self.failing_opener)
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
python3 tasks/web-exploration/environment/webarena/test_runtime.py
```

Expected: import failure because `runtime.py` does not exist.

- [ ] **Step 3: Implement the stdlib reset client**

Use `urllib.request`; do not add `requests`:

```python
def require_http_ok(url: str, method: str = "GET", opener=urlopen) -> bytes:
    request = Request(url, method=method)
    try:
        with opener(request, timeout=RESET_TIMEOUT_SEC) as response:
            if not 200 <= response.status < 300:
                raise RuntimeError(f"{method} {url} returned {response.status}")
            return response.read()
    except (OSError, HTTPError, URLError) as exc:
        raise RuntimeError(f"{method} {url} failed: {exc}") from exc

def reset_site() -> None:
    require_http_ok(f"{CONTROL_URL}/reset", method="POST")
    deadline = time.monotonic() + RESET_TIMEOUT_SEC
    while time.monotonic() < deadline:
        try:
            require_http_ok(f"{CONTROL_URL}/status")
            require_http_ok(SHOPPING_URL)
            return
        except RuntimeError:
            time.sleep(2)
    raise RuntimeError("Shopping reset failed health check")
```

- [ ] **Step 4: Implement direct `agent-browser` commands**

Use one fixed per-step session configured by `AGENT_BROWSER_SESSION`:

```python
def browser(args: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["agent-browser", "--session", SESSION, "--json", *args],
        check=check,
        text=True,
        capture_output=True,
    )

def prepare(task_id: int, task: dict | None = None) -> None:
    task = task or load_task(task_id)
    reset_site()
    APP.mkdir(parents=True, exist_ok=True)
    TASK_PATH.write_text(json.dumps(task, indent=2) + "\n")
    for path in (RESPONSE_PATH, HAR_PATH):
        path.unlink(missing_ok=True)
    browser(["close"], check=False)
    browser(["open"])
    browser(["state", "load", AUTH_STATE])
    browser(["network", "har", "start", "--content", "text"])
```

`capture-stop` must save to `/logs/agent/network.har` and fail if the file is absent or invalid JSON.

- [ ] **Step 5: Implement HAR metrics**

Count only normalized URLs on the configured Shopping origin:

```python
def har_metrics(har: dict, shopping_url: str) -> dict[str, float]:
    origin = urlsplit(shopping_url)
    urls = {
        (parts.scheme, parts.netloc, parts.path)
        for entry in har.get("log", {}).get("entries", [])
        if (parts := urlsplit(entry.get("request", {}).get("url", "")))
        and (parts.scheme, parts.netloc) == (origin.scheme, origin.netloc)
    }
    return {"unique_urls": float(len(urls))}
```

Parse `/logs/agent/trajectory.json` recursively and count shell commands containing the token `agent-browser`; expose `agent_browser_commands` as a float.

- [ ] **Step 6: Run tests**

Run:

```bash
python3 tasks/web-exploration/environment/webarena/test_runtime.py
```

Expected: all tests pass without Docker or network access.

- [ ] **Step 7: Commit**

```bash
git add tasks/web-exploration/environment
git commit -m "feat: add WebArena browser runtime"
```

---

### Task 3: Official Evaluator Integration

**Files:**
- Modify: `tasks/web-exploration/environment/webarena/runtime.py`
- Modify: `tasks/web-exploration/environment/webarena/test_runtime.py`
- Delete: `tasks/web-exploration/tests/test.sh`
- Delete: `tasks/web-exploration/tests/reward.toml`
- Delete: `tasks/web-exploration/tests/correctness/check.py`

**Interfaces:**
- Consumes `/app/agent_response.json`, `/logs/agent/network.har`, task ID, and `/opt/webarena/config.json`.
- Produces `/logs/verifier/reward.json`.

- [ ] **Step 1: Write evaluator tests**

Inject the evaluator so unit tests do not require the package:

```python
def test_evaluate_writes_reward_and_metrics(self):
    fake_result = SimpleNamespace(score=1.0, status="SUCCESS")
    evaluator = mock.Mock()
    evaluator.evaluate_task.return_value = fake_result
    reward = runtime.evaluate(21, evaluator=evaluator, metrics={"unique_urls": 4.0, "agent_browser_commands": 7.0})
    self.assertEqual(1.0, reward["reward"])
    self.assertEqual(4.0, reward["unique_urls"])
    self.assertEqual(7.0, reward["agent_browser_commands"])

def test_missing_response_is_infrastructure_error(self):
    with self.assertRaisesRegex(RuntimeError, "agent_response.json is missing"):
        runtime.evaluate(21, evaluator=mock.Mock(), response_path=self.missing_path)
```

- [ ] **Step 2: Run the focused test and verify failure**

Run:

```bash
python3 tasks/web-exploration/environment/webarena/test_runtime.py
```

Expected: failure because `evaluate` is not implemented.

- [ ] **Step 3: Implement the official API call**

Use the stable high-level API:

```python
from webarena_verified.api import WebArenaVerified
from webarena_verified.types.config import WebArenaVerifiedConfig

def build_evaluator() -> WebArenaVerified:
    config = WebArenaVerifiedConfig.model_validate_json(CONFIG_PATH.read_text())
    return WebArenaVerified(config=config)

def evaluate(
    task_id: int,
    evaluator=None,
    metrics: dict[str, float] | None = None,
    response_path: Path = RESPONSE_PATH,
) -> dict[str, float]:
    if not response_path.is_file():
        raise RuntimeError("agent_response.json is missing")
    if not HAR_PATH.is_file():
        raise RuntimeError("network.har is missing")
    result = (evaluator or build_evaluator()).evaluate_task(
        task_id=task_id,
        agent_response=response_path,
        network_trace=HAR_PATH,
    )
    reward = {"reward": float(result.score), **(metrics or collect_metrics())}
    REWARD_PATH.parent.mkdir(parents=True, exist_ok=True)
    REWARD_PATH.write_text(json.dumps(reward) + "\n")
    return reward
```

Do not catch evaluator exceptions. Incorrect valid responses return zero; broken evaluation fails.

- [ ] **Step 4: Replace Reward Kit hooks**

Generated step `tests/test.sh` must contain only:

```bash
#!/usr/bin/env bash
set -euo pipefail
runuser -u agent -- python3 /opt/webarena/runtime.py capture-stop
python3 /opt/webarena/runtime.py evaluate "$TASK_ID"
```

Pass the concrete task ID when generating each script instead of depending on a mutable environment variable.

- [ ] **Step 5: Run runtime tests**

Run:

```bash
python3 tasks/web-exploration/environment/webarena/test_runtime.py
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add tasks/web-exploration/environment/webarena tasks/web-exploration/tests
git commit -m "feat: score tasks with WebArena Verified"
```

---

### Task 4: Task Image and Pi Skill

**Files:**
- Modify: `tasks/web-exploration/environment/Dockerfile`
- Modify: `tasks/web-exploration/environment/.dockerignore`

**Interfaces:**
- Produces an `agent` user with `agent-browser` on `PATH`.
- Produces Pi-discoverable `/app/.pi/skills/agent-browser/SKILL.md`.
- Produces root-owned `/opt/webarena/{runtime.py,dataset.json,agent-input.json,auth.json,config.json}`.

- [ ] **Step 1: Add a static Dockerfile check**

Extend `test_generate_steps.py`:

```python
def test_dockerfile_pins_external_tools(self):
    text = (ROOT / "environment" / "Dockerfile").read_text()
    self.assertIn("agent-browser@0.36.0", text)
    self.assertIn("webarena-verified==1.2.3", text)
    self.assertIn("/app/.pi/skills/agent-browser", text)
```

- [ ] **Step 2: Verify the check fails**

Run:

```bash
python3 -m unittest tasks.web-exploration.test_generate_steps -v
```

Expected: failure because the old Dockerfile contains none of the pins.

- [ ] **Step 3: Replace the Dockerfile**

Use Ubuntu 24.04, install Node 22 from the official NodeSource repository, then:

```dockerfile
COPY --from=ghcr.io/astral-sh/uv:0.9.7 /uv /usr/local/bin/uv
ENV UV_BREAK_SYSTEM_PACKAGES=1
RUN uv pip install --python /usr/bin/python3 --system 'webarena-verified==1.2.3' \
    && npm install -g 'agent-browser@0.36.0' \
    && agent-browser install --with-deps

RUN mkdir -p /app/.pi/skills /app/sessions /opt/webarena /logs/agent /logs/verifier \
    && cp -R "$(npm root -g)/agent-browser/skills/agent-browser" \
       /app/.pi/skills/agent-browser
```

Copy `data/` plus the runtime and evaluator config under `/opt/webarena`. The image may build before `auth.json` exists, but `prepare` must fail explicitly until it is present. Make `/opt/webarena` root-owned and unreadable except for the specific runtime inputs needed by the `agent` process. Make `/app` and `/logs/agent` writable by `agent`.

Set:

```dockerfile
ENV AGENT_BROWSER_SESSION=webarena-shopping
ENV WEBARENA_SHOPPING_URL=http://host.docker.internal:7770
ENV WEBARENA_CONTROL_URL=http://host.docker.internal:7771
ENV WEBARENA_AUTH_STATE=/opt/webarena/auth.json
WORKDIR /app
```

- [ ] **Step 4: Run static tests and build**

Run:

```bash
python3 -m unittest tasks.web-exploration.test_generate_steps -v
docker build -t agent-learning-bench-webarena-shopping tasks/web-exploration/environment
```

Expected: tests pass and image builds with pinned versions.

- [ ] **Step 5: Verify the image**

Run:

```bash
docker run --rm agent-learning-bench-webarena-shopping \
  bash -lc 'agent-browser --version && python3 -c "import webarena_verified" && test -f /app/.pi/skills/agent-browser/SKILL.md'
```

Expected: `agent-browser 0.36.0`, successful Python import, zero exit.

- [ ] **Step 6: Commit**

```bash
git add tasks/web-exploration/environment/Dockerfile \
  tasks/web-exploration/environment/.dockerignore \
  tasks/web-exploration/test_generate_steps.py
git commit -m "build: add WebArena browser environment"
```

---

### Task 5: Harbor Step Contract and Instructions

**Files:**
- Modify: `tasks/web-exploration/instruction.md`
- Modify: `tasks/web-exploration/generate_steps.py`
- Modify: `tasks/web-exploration/test_generate_steps.py`

**Interfaces:**
- Agent reads `/app/task.json`.
- Agent uses the installed `agent-browser` skill and CLI.
- Agent writes `/app/agent_response.json`.

- [ ] **Step 1: Add generated-step contract tests**

```python
def test_generated_step_contract(self):
    generate(self.shopping_rows(3), self.temp_root, limit=None)
    setup = (self.temp_root / "steps/task-0021/workdir/setup.sh").read_text()
    verify = (self.temp_root / "steps/task-0021/tests/test.sh").read_text()
    manifest = (self.temp_root / "task.toml").read_text()
    self.assertIn("runtime.py prepare 21", setup)
    self.assertIn("runtime.py evaluate 21", verify)
    self.assertEqual(3, manifest.count("[[steps]]"))
    self.assertIn('artifacts = ["/app/agent_response.json", "/app/task.json", "/app/notes.md", "/app/sessions", "/logs/agent/network.har"]', manifest)
```

- [ ] **Step 2: Run and verify failure**

Run:

```bash
python3 -m unittest tasks.web-exploration.test_generate_steps -v
```

Expected: failure against the old `q-NNN` generation contract.

- [ ] **Step 3: Write the static instruction**

Keep it short:

```markdown
# WebArena Shopping

Read `/app/task.json`. Complete its `intent` on its `start_urls` using the installed `agent-browser` skill and CLI.

Read `/app/notes.md` and `/app/sessions/` when useful. Update `/app/notes.md` with reusable knowledge about the Shopping site, not task-specific answers.

Write `/app/agent_response.json` in the WebArena-Verified schema:

{"task_type":"RETRIEVE|NAVIGATE|MUTATE","status":"SUCCESS","retrieved_data":null,"error_details":null}

Use the typed result format requested by the task. Stop after writing the response.
```

- [ ] **Step 4: Generate the Harbor contract**

The manifest must use schema 1.4, `multi_step_reward_strategy = "mean"`, agent user `agent`, public network, 300-second agent timeout, 180-second verifier timeout, and the artifacts asserted in the test.

Each setup script contains:

```bash
python3 /opt/webarena/runtime.py prepare 21
rm -- "$0"
```

Each verifier script contains the capture/evaluate commands from Task 3.

- [ ] **Step 5: Run tests and generate all tasks**

Run:

```bash
python3 -m unittest tasks.web-exploration.test_generate_steps -v
python3 tasks/web-exploration/generate_steps.py
```

Expected: tests pass and generator prints `wrote 187 steps`.

- [ ] **Step 6: Commit**

```bash
git add tasks/web-exploration/instruction.md tasks/web-exploration/generate_steps.py \
  tasks/web-exploration/test_generate_steps.py
git commit -m "feat: define WebArena Harbor task contract"
```

---

### Task 6: Setup Documentation and Smoke Validation

**Files:**
- Modify: `tasks/web-exploration/README.md`
- Modify: `README.md`

**Interfaces:**
- Documents external Shopping service ports `7770` and `7771`.
- Documents creation of `data/auth.json` using the official WebArena authentication tooling.
- Documents identical three-task and full-run commands for all three conditions.

- [ ] **Step 1: Replace the task README**

Document, in order:

1. Required Docker, Harbor, OpenAI key, disk requirement, and supported macOS Docker host URL.
2. Start the official Shopping image:

```bash
webarena-verified env start --site shopping
curl http://localhost:7771/status
```

3. Create the official Shopping storage state without putting credentials in the agent prompt:

```bash
git clone https://github.com/web-arena-x/webarena.git /tmp/webarena
git -C /tmp/webarena checkout dce04686a56253aefba7b18a4fa0937cf1dc987b
python3 -m pip install -r /tmp/webarena/requirements.txt
python3 -m playwright install chromium
SHOPPING=http://localhost:7770 \
SHOPPING_ADMIN=unused REDDIT=unused GITLAB=unused \
WIKIPEDIA=unused MAP=unused HOMEPAGE=unused \
python3 /tmp/webarena/browser_env/auto_login.py \
  --site_list shopping \
  --auth_folder "$PWD/tasks/web-exploration/data"
mv tasks/web-exploration/data/shopping_state.json \
   tasks/web-exploration/data/auth.json
```
4. Fetch and generate:

```bash
./tasks/web-exploration/download.sh
python3 tasks/web-exploration/generate_steps.py --n 3
```

5. Run the three-task smoke conditions with distinct job names.
6. Regenerate all 187 tasks and run each full condition separately.
7. Explain that all full runs total 561 model-backed steps.
8. Run reporting:

```bash
python3 tools/report_runs.py --task web-exploration --out-dir reports
```

- [ ] **Step 2: Update root task description**

Replace references to the fictional Kestrel Depot site with WebArena-Verified Shopping, 187 Shopping-only tasks, `agent-browser`, and the external-service prerequisite. Do not change unrelated task documentation.

- [ ] **Step 3: Run all offline tests**

Run:

```bash
python3 -m unittest tasks.web-exploration.test_generate_steps -v
python3 tasks/web-exploration/environment/webarena/test_runtime.py
python3 tasks/report-check/test_engine.py
python3 tasks/warden/test_engine.py
```

Expected: all pass.

- [ ] **Step 4: Run environment smoke validation when prerequisites exist**

Run:

```bash
python3 tasks/web-exploration/generate_steps.py --n 3
harbor run -p tasks/web-exploration -a oracle --job-name webarena-shopping-oracle-smoke
```

Expected: three completed step results, valid HAR per step, reset succeeds before each task, and no infrastructure exception.

If Harbor, Docker, Shopping, or auth state is unavailable, stop after the offline tests and report the missing prerequisite. Do not install it automatically.

- [ ] **Step 5: Commit**

```bash
git add README.md tasks/web-exploration/README.md
git commit -m "docs: explain WebArena shopping runs"
```

---

## Final Verification

- [ ] Generate all tasks and confirm count:

```bash
python3 tasks/web-exploration/generate_steps.py
test "$(rg -c '^\[\[steps\]\]$' tasks/web-exploration/task.toml)" -eq 187
```

- [ ] Run all offline tests:

```bash
python3 -m unittest tasks.web-exploration.test_generate_steps -v
python3 tasks/web-exploration/environment/webarena/test_runtime.py
python3 tasks/report-check/test_engine.py
python3 tasks/warden/test_engine.py
```

- [ ] Confirm branch contains no generated or secret data:

```bash
git status --short
git ls-files tasks/web-exploration/data tasks/web-exploration/steps \
  tasks/web-exploration/task.toml
```

Expected: clean worktree; no output from `git ls-files`.

- [ ] Review the diff against the approved design:

```bash
git diff main...HEAD --stat
git log --oneline main..HEAD
```

