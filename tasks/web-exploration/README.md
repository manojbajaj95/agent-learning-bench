# Web exploration

Evaluate Harbor `pi` on all 187 Shopping-only tasks from the pinned
[WebArena-Verified](https://github.com/ServiceNow/webarena-verified) dataset.
The benchmark uses the official WebArena Shopping service, not a bundled mock.

This task runs the **baseline** agent only (`pi`, fresh chat each step).

## Prerequisites

- Docker Desktop with the `docker` CLI on `PATH` (or `~/.docker/bin/docker`)
- Enough free disk for the 17.8 GB Shopping image
- [Harbor](https://www.harborframework.com/docs)
- `OPENAI_API_KEY`
- On the host, `host.docker.internal` must resolve to this machine so Magento
  and the Harbor container share one origin. If
  `python3 -c 'import socket; print(socket.gethostbyname("host.docker.internal"))'`
  fails, add `127.0.0.1 host.docker.internal` to `/etc/hosts`.

Use the OpenAI model id `gpt-5.6-luna` (dot, not hyphen).

Paste each command as a single line. A line break turns the next flag into a
zsh command, for example `zsh: command not found: --agent-timeout-multiplier`.

## Entire setup

Keep the broker running in one terminal. Harbor runs in another.

```bash
python3 tasks/web-exploration/reset_broker.py
```

First time only, wait until Shopping is healthy:

```bash
curl -X POST http://localhost:7772/reset
curl http://localhost:7772/status
```

Then download the dataset once:

```bash
./tasks/web-exploration/download.sh
```

Smoke is three tasks to check the image. Full is the 187-task run. Pick one.
If you smoke first, regenerate all 187 steps before full.

### Three-task smoke (optional)

```bash
python3 tasks/web-exploration/generate_steps.py --n 3
harbor run -p tasks/web-exploration -a pi -m openai/gpt-5.6-luna --agent-timeout-multiplier 5 --job-name webarena-shopping-baseline-smoke-3
```

### All 187 tasks

```bash
python3 tasks/web-exploration/generate_steps.py
harbor run -p tasks/web-exploration -a pi -m openai/gpt-5.6-luna --agent-timeout-multiplier 5 --job-name webarena-shopping-baseline-full-v2
```

Each Harbor step recreates Magento, then logs in after each reset as the
official WebArena shopping customer. Do not generate cookie files; Magento
login state does not survive reset.

Shopping is served at `http://host.docker.internal:7770` (port `7770` on the
host). Env-ctrl stays on `7771` for the broker's health checks. Harbor task
containers call the broker at `http://host.docker.internal:7772`. The first
reset downloads the Shopping image and can take several minutes.

The benchmark image installs the `agent-browser` skill and CLI. The agent
uses it to operate Shopping. The verifier scores the response and HAR with
WebArena-Verified.
