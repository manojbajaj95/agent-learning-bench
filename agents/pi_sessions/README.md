# pi-sessions (sample Harbor agent)

Thin wrapper around Harbor’s built-in [pi](https://pi.dev/) agent. One TypeScript
extension copies each session JSONL into `/app/sessions/` when the session shuts down
(`session_shutdown`).

Later steps in the same Harbor trial share the container filesystem, so the agent can
read prior logs under `/app/sessions/` with pi’s normal file tools. A new trial starts a
new container, so sessions do not spill across trials.

## Layout

```
agents/pi_sessions/
├── agent.py                 # PiSessionsAgent (subclass of harbor Pi)
├── extensions/
│   └── save-sessions.ts     # session_shutdown → /app/sessions/
└── README.md
```

## Run

From the repo root:

```bash
PYTHONPATH=. harbor run -p tasks/sample \
  -a agents.pi_sessions:PiSessionsAgent \
  -m openai/gpt-5.6-luna \
  --agent-timeout-multiplier 5
```

Needs `OPENAI_API_KEY`. Raise the agent timeout multiplier if turns time out (pi is slower than terminus-2).

## Behavior

1. Installs pi (same as Harbor `pi`).
2. Uploads `save-sessions.ts` to `/opt/pi-sessions/save-sessions.ts`.
3. Runs `pi … -e /opt/pi-sessions/save-sessions.ts` with session dir
   `/logs/agent/pi/sessions`.
4. On `session_shutdown`, the extension copies the session file to `/app/sessions/`.
