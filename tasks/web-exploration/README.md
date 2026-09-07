# Web exploration

Evaluate learning across all 187 Shopping-only tasks from the pinned
[WebArena-Verified](https://github.com/ServiceNow/webarena-verified) dataset.
The benchmark uses the official WebArena Shopping service, not a bundled mock.

## Prerequisites

- Docker with enough free disk for the 17.8 GB Shopping image
- [Harbor](https://www.harborframework.com/docs)
- `OPENAI_API_KEY`
- The `webarena-verified` command
- On macOS, a Docker setup that supports `http://host.docker.internal`; the
  benchmark container reaches the host services through
  `http://host.docker.internal:7770` and `http://host.docker.internal:7771`

Use the OpenAI model id `gpt-5.6-luna` (dot, not hyphen).

## Start Shopping

From the repository root, start the official Shopping image and wait for its
reset controller to report healthy:

```bash
webarena-verified env start --site shopping
curl http://localhost:7771/status
```

Shopping is served on port `7770`; the reset controller is on port `7771`.
Before every task, the benchmark posts to the controller's `/reset` endpoint,
waits for both services to become healthy, loads the saved authentication
state, and starts a fresh network capture.

## Create the authentication state

Generate the official Shopping storage state locally. Credentials stay in the
browser state file and are never placed in the agent prompt.

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

`data/auth.json` is generated, secret-bearing input and is gitignored.

## Fetch and generate the smoke tasks

Download the pinned dataset and generate the first three Shopping tasks:

```bash
./tasks/web-exploration/download.sh
python3 tasks/web-exploration/generate_steps.py --n 3
```

The benchmark image installs the `agent-browser` skill and CLI. Each agent
uses it to operate Shopping, while the verifier evaluates the final response
and the captured HAR with WebArena-Verified.

## Run the three-task smoke

Run all three learning conditions with distinct job names:

```bash
harbor run -p tasks/web-exploration -a pi -m openai/gpt-5.6-luna \
  --agent-timeout-multiplier 5 \
  --job-name webarena-shopping-baseline-smoke

PYTHONPATH=. harbor run -p tasks/web-exploration \
  -a agents.pi_sessions:PiSessionsAgent \
  -m openai/gpt-5.6-luna \
  --agent-timeout-multiplier 5 \
  --job-name webarena-shopping-pi-sessions-smoke

harbor run -p tasks/web-exploration -a pi -m openai/gpt-5.6-luna \
  --resume-trajectory \
  --agent-timeout-multiplier 5 \
  --job-name webarena-shopping-in-context-smoke
```

Smoke first: do not start a full run until each condition completes its three
tasks, produces valid step results and HAR files, and resets Shopping before
each task.

## Run all 187 tasks

Regenerate the task to include all 187 Shopping-only steps, then run each
condition separately:

```bash
python3 tasks/web-exploration/generate_steps.py

harbor run -p tasks/web-exploration -a pi -m openai/gpt-5.6-luna \
  --agent-timeout-multiplier 5 \
  --job-name webarena-shopping-baseline-full

PYTHONPATH=. harbor run -p tasks/web-exploration \
  -a agents.pi_sessions:PiSessionsAgent \
  -m openai/gpt-5.6-luna \
  --agent-timeout-multiplier 5 \
  --job-name webarena-shopping-pi-sessions-full

harbor run -p tasks/web-exploration -a pi -m openai/gpt-5.6-luna \
  --resume-trajectory \
  --agent-timeout-multiplier 5 \
  --job-name webarena-shopping-in-context-full
```

The baseline, pi-sessions, and in-context conditions each run 187 tasks, for
561 total model-backed steps.

## Report the runs

```bash
python3 tools/report_runs.py --task web-exploration --out-dir reports
```
