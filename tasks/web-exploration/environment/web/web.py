#!/usr/bin/env python3
"""Kestrel Depot intranet CLI and step helpers."""

from __future__ import annotations

import html
import json
import os
import re
import runpy
import sys
from pathlib import Path

ROOT = Path(os.environ.get("WEB_ROOT", "/opt/web"))
APP = Path(os.environ.get("WEB_APP", "/app"))
QUESTIONS_PATH = ROOT / "questions.json"
GOLD_PATH = ROOT / "gold.json"
PAGES_PATH = ROOT / "pages.py"
STATE_DIR = ROOT / "state"
ACCESS_PATH = STATE_DIR / "access.jsonl"
SUBMISSIONS_PATH = STATE_DIR / "submissions.jsonl"
SEQ_PATH = STATE_DIR / "seq.json"
STEP_PATH = APP / ".step.txt"
QUESTION_PATH = APP / "question.md"
ANSWER_PATH = APP / "answer.json"
TRAJECTORY_PATH = Path("/logs/agent/trajectory.json")
REWARD_PATH = Path("/logs/verifier/reward.json")

NAV = [
    ("Home", "/"),
    ("About", "/about"),
    ("Locations", "/locations"),
    ("Catalog", "/catalog"),
    ("Pricing", "/pricing"),
    ("Support", "/support"),
    ("Policies", "/policies"),
    ("Team", "/team"),
    ("News", "/news"),
    ("Forms", "/forms"),
]


def _pages() -> dict:
    try:
        return runpy.run_path(str(PAGES_PATH))["PAGES"]
    except (FileNotFoundError, PermissionError):
        raise SystemExit("intranet pages are not readable; use: web get <path>")


def _form_prefix() -> dict:
    try:
        return runpy.run_path(str(PAGES_PATH))["FORM_PREFIX"]
    except (FileNotFoundError, PermissionError):
        raise SystemExit("intranet pages are not readable; use: web post <path> field=value ...")


def _step() -> str:
    return STEP_PATH.read_text().strip() if STEP_PATH.exists() else ""


def _log_access(method: str, path: str) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    rec = {"step": _step(), "method": method, "path": path}
    with ACCESS_PATH.open("a") as f:
        f.write(json.dumps(rec) + "\n")


def _layout(title: str, body: str) -> str:
    links = " ".join(
        f'<a href="{html.escape(href)}">{html.escape(label)}</a>' for label, href in NAV
    )
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<title>{html.escape(title)}</title>"
        "<style>body{font-family:sans-serif;max-width:720px;margin:2em auto;line-height:1.4}"
        "nav{margin-bottom:1em}nav a{margin-right:0.8em}form p{margin:0.5em 0}</style>"
        f"</head><body><nav>{links}</nav><h1>{html.escape(title)}</h1>{body}</body></html>\n"
    )


def _render_form(spec: dict) -> str:
    parts = [f"<form action=\"{html.escape(spec['action'])}\" method=\"post\">"]
    for field in spec["fields"]:
        name = html.escape(field["name"])
        label = html.escape(field["label"])
        if field.get("type") == "textarea":
            parts.append(
                f"<p><label>{label}<br><textarea name=\"{name}\"></textarea></label></p>"
            )
        else:
            parts.append(
                f"<p><label>{label}<br><input name=\"{name}\"></label></p>"
            )
    parts.append("<p><button type=\"submit\">Submit</button></p></form>")
    parts.append(
        "<p>CLI: <code>web post "
        + html.escape(spec["action"])
        + " "
        + " ".join(f"{html.escape(f['name'])}=..." for f in spec["fields"])
        + "</code></p>"
    )
    return "".join(parts)


def render(path: str, extra: str = "") -> tuple[str, bool]:
    pages = _pages()
    page = pages.get(path)
    if page is None:
        return _layout("Not found", f"<p>No page at {html.escape(path)}.</p>"), False
    chunks = []
    if page.get("lead"):
        chunks.append(f"<p><strong>{html.escape(page['lead'])}</strong></p>")
    for para in page.get("paragraphs") or []:
        chunks.append(f"<p>{html.escape(para)}</p>")
    if page.get("form"):
        chunks.append(_render_form(page["form"]))
    if page.get("links"):
        items = "".join(
            f'<li><a href="{html.escape(href)}">{html.escape(label)}</a></li>'
            for label, href in page["links"]
        )
        chunks.append(f"<ul>{items}</ul>")
    if extra:
        chunks.append(extra)
    return _layout(page["title"], "".join(chunks)), True


def respond_get(path: str) -> tuple[str, int]:
    if not path.startswith("/"):
        path = "/" + path
    html_out, ok = render(path)
    _log_access("GET", path)
    return html_out, 200 if ok else 404


def cmd_get(path: str) -> None:
    html_out, code = respond_get(path)
    sys.stdout.write(html_out)
    if code != 200:
        raise SystemExit(1)


def _parse_fields(args: list[str]) -> dict[str, str]:
    fields: dict[str, str] = {}
    for arg in args:
        key, sep, value = arg.partition("=")
        if not sep:
            raise SystemExit(f"expected field=value, got {arg!r}")
        fields[key] = value
    return fields


def _next_code(prefix: str) -> str:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    seq = {}
    if SEQ_PATH.exists():
        seq = json.loads(SEQ_PATH.read_text())
    n = int(seq.get(prefix, 0)) + 1
    seq[prefix] = n
    SEQ_PATH.write_text(json.dumps(seq) + "\n")
    return f"{prefix}-{n:04d}"


def respond_post(path: str, fields: dict[str, str]) -> tuple[str, int]:
    if not path.startswith("/"):
        path = "/" + path
    pages = _pages()
    page = pages.get(path)
    prefixes = _form_prefix()
    if page is None or not page.get("form") or path not in prefixes:
        _log_access("POST", path)
        return _layout("Not found", f"<p>No form at {html.escape(path)}.</p>"), 404
    required = [f["name"] for f in page["form"]["fields"]]
    missing = [name for name in required if not str(fields.get(name, "")).strip()]
    if missing:
        _log_access("POST", path)
        extra = "<p>Missing fields: " + html.escape(", ".join(missing)) + ".</p>"
        html_out, _ = render(path, extra)
        return html_out, 400
    code = _next_code(prefixes[path])
    rec = {
        "step": _step(),
        "path": path,
        "fields": fields,
        "confirmation": code,
    }
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with SUBMISSIONS_PATH.open("a") as f:
        f.write(json.dumps(rec) + "\n")
    _log_access("POST", path)
    extra = f"<p>Confirmation: <strong>{html.escape(code)}</strong></p>"
    html_out, _ = render(path, extra)
    return html_out, 200


def cmd_post(path: str, args: list[str]) -> None:
    html_out, code = respond_post(path, _parse_fields(args))
    sys.stdout.write(html_out)
    if code != 200:
        raise SystemExit(1)


def cmd_serve(host: str = "127.0.0.1", port: int = 8765) -> None:
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from urllib.parse import parse_qs, unquote, urlparse

    class Handler(BaseHTTPRequestHandler):
        def _send(self, body: str, status: int) -> None:
            data = body.encode()
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:
            path = unquote(urlparse(self.path).path) or "/"
            body, status = respond_get(path)
            self._send(body, status)

        def do_POST(self) -> None:
            path = unquote(urlparse(self.path).path) or "/"
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length).decode() if length else ""
            parsed = parse_qs(raw, keep_blank_values=True)
            fields = {k: (v[-1] if v else "") for k, v in parsed.items()}
            body, status = respond_post(path, fields)
            self._send(body, status)

        def log_message(self, fmt: str, *args) -> None:
            sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Kestrel Depot at http://{host}:{port}/", flush=True)
    server.serve_forever()


def cmd_publish(index: str) -> None:
    n = int(index)
    questions = json.loads(QUESTIONS_PATH.read_text())
    item = questions[n - 1]
    STEP_PATH.write_text(str(n) + "\n")
    QUESTION_PATH.write_text(
        f"Job {n} of {len(questions)}\n\n{item['question']}\n"
    )
    if ANSWER_PATH.exists():
        ANSWER_PATH.unlink()


def _norm(value) -> str:
    text = str(value).strip().casefold()
    text = text.replace("$", "").replace(",", "")
    return re.sub(r"\s+", " ", text)


def answers_match(pred, gold: str) -> bool:
    if isinstance(pred, dict) and "answer" in pred:
        pred = pred["answer"]
    return _norm(pred) == _norm(gold)


def _load_answer() -> dict | None:
    if not ANSWER_PATH.exists():
        return None
    try:
        data = json.loads(ANSWER_PATH.read_text())
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _submissions_for_step(step: str) -> list[dict]:
    if not SUBMISSIONS_PATH.exists():
        return []
    out = []
    for line in SUBMISSIONS_PATH.read_text().splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if rec.get("step") == step:
            out.append(rec)
    return out


def action_ok(gold: dict) -> bool:
    pred = _load_answer()
    if pred is None or "answer" not in pred:
        return False
    step = _step()
    expected = {k: _norm(v) for k, v in (gold.get("fields") or {}).items()}
    for rec in _submissions_for_step(step):
        if rec.get("path") != gold.get("endpoint"):
            continue
        got = {k: _norm(v) for k, v in (rec.get("fields") or {}).items()}
        if any(got.get(k) != v for k, v in expected.items()):
            continue
        if _norm(pred.get("answer")) == _norm(rec.get("confirmation")):
            return True
    return False


def qa_ok(gold: dict) -> bool:
    pred = _load_answer()
    if pred is None:
        return False
    return answers_match(pred, gold["answer"])


def grade() -> bool:
    if not STEP_PATH.exists() or not GOLD_PATH.exists():
        return False
    step = int(STEP_PATH.read_text().strip())
    gold = json.loads(GOLD_PATH.read_text())[step - 1]
    if gold.get("kind") == "action":
        return action_ok(gold)
    return qa_ok(gold)


def _trajectory_metrics() -> tuple[int, int]:
    if not TRAJECTORY_PATH.exists():
        return 0, 0
    data = json.loads(TRAJECTORY_PATH.read_text())
    final = data.get("final_metrics") or {}
    tokens = int(final.get("total_prompt_tokens") or 0) + int(
        final.get("total_completion_tokens") or 0
    )
    tool_calls = 0
    for step in data.get("steps") or []:
        tool_calls += len(step.get("tool_calls") or [])
    if not tool_calls:
        tool_calls = int(final.get("total_steps") or 0)
    return tool_calls, tokens


def cmd_costs() -> None:
    step = _step()
    paths: set[str] = set()
    if ACCESS_PATH.exists():
        for line in ACCESS_PATH.read_text().splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            if not step or rec.get("step") == step:
                paths.add(rec.get("path") or "")
    tool_calls, tokens = _trajectory_metrics()
    REWARD_PATH.parent.mkdir(parents=True, exist_ok=True)
    rewards = {}
    if REWARD_PATH.exists():
        try:
            rewards = json.loads(REWARD_PATH.read_text())
        except json.JSONDecodeError:
            rewards = {}
    rewards["pages_visited"] = float(len(paths))
    rewards["tool_calls"] = float(tool_calls)
    rewards["tokens"] = float(tokens)
    REWARD_PATH.write_text(json.dumps(rewards) + "\n")


def main(argv: list[str]) -> None:
    if not argv:
        raise SystemExit("usage: web.py get|post|publish|costs|serve ...")
    cmd = argv[0]
    if cmd == "get":
        if len(argv) < 2:
            raise SystemExit("usage: web.py get <path>")
        cmd_get(argv[1])
    elif cmd == "post":
        if len(argv) < 2:
            raise SystemExit("usage: web.py post <path> field=value ...")
        cmd_post(argv[1], argv[2:])
    elif cmd == "publish":
        if len(argv) < 2:
            raise SystemExit("usage: web.py publish <1-based-index>")
        cmd_publish(argv[1])
    elif cmd == "costs":
        cmd_costs()
    elif cmd == "serve":
        host = "127.0.0.1"
        port = 8765
        if len(argv) > 1:
            port = int(argv[1])
        cmd_serve(host, port)
    else:
        raise SystemExit(f"unknown command: {cmd}")


if __name__ == "__main__":
    main(sys.argv[1:])
