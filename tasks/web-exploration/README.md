# Web exploration

The agent completes 187 Shopping tasks on one pinned WebArena site. Success should stay high while page visits and tokens fall.

## Task type

Non-verifiable. WebArena-Verified scores the response and the HAR after the step. That score does not return to the agent. The agent can browse the site during the step.

## Labels

`fixed`, `unordered`. The pinned Shopping site stays the same on every run. Each step resets the site, so task order does not change the world.

## Environment

The site is the official WebArena Shopping service. It is not a mock inside the image.

- Shopping: `http://host.docker.internal:7770`
- Env-ctrl: port `7771` on the host
- Reset broker: `http://host.docker.internal:7772`
- Shopping image: about 17.8 GB, downloaded on the first reset
- Agent tools: `agent-browser` CLI and skill in the task image
- Network: `public`
- Agent timeout: 180 seconds per task
- Dataset pin: WebArena-Verified commit `6473f72`

`host.docker.internal` must resolve to this machine. If it does not, add `127.0.0.1 host.docker.internal` to `/etc/hosts`.

Each step resets Magento, then logs in as the WebArena shopping customer. Login state does not survive a reset. Do not generate cookie files.

`steps/` and `task.toml` are generated and gitignored. A new trial starts a new Harbor container. The Shopping service stays up on the host.

## Step design

One trial is 187 Shopping-only tasks. One step is one task. The agent writes a response. The verifier scores that response and the network HAR.

```bash
./tasks/web-exploration/download.sh
python3 tasks/web-exploration/generate_steps.py --n 3   # smoke
python3 tasks/web-exploration/generate_steps.py         # all 187
```

If you generate a smoke slice, generate all 187 steps again before a full run. This task has no separate holdout split in the README. Later tasks on the same site are the transfer check.

## Learning goal

The learning object is the Shopping site structure and the navigation that repeats across tasks. Accuracy should stay high while `pages_visited` and tokens fall. Baseline starts a fresh chat each task. In-context learning resumes the same chat. Compare them on the same task order.

## Reward and cost

Harbor averages the per-task reward (`multi_step_reward_strategy = "mean"`). The verifier writes `/logs/verifier/reward.json`:

| Field | Meaning |
|---|---|
| `reward` | WebArena-Verified score |
| `correctness` | Same score |
| `pages_visited` | Pages recorded for the step |
| `tool_calls` | Tool calls in the step trajectory |
| `tokens` | Prompt tokens plus completion tokens in that trajectory |

Harbor also records `cost_usd`, input tokens, output tokens, and step duration.

## Running

Needs Docker, Harbor, and `OPENAI_API_KEY`. The model id is `openai/gpt-5.6-luna`. Keep the broker in one terminal:

```bash
python3 tasks/web-exploration/reset_broker.py
```

Wait until Shopping is healthy. `/reset` returns immediately. Repeat `/status` until it reports `"success": true`:

```bash
curl -X POST http://localhost:7772/reset
curl http://localhost:7772/status
```

Paste each Harbor command as one line.

```bash
alb prepare web-exploration
alb run web-exploration --system baseline
alb run web-exploration --system icl
```

`alb prepare` downloads the dataset when `data/` is empty, then generates steps.
