"""Exercise real entrypoints with injected paths; Docker tests cover OS privileges."""

import importlib.util
import io
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

TASK = Path(__file__).resolve().parents[1]


def load_entrypoint(name):
    spec = importlib.util.spec_from_file_location(
        f"language_{name}", TASK / f"environment/{name}.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_public_stdin_errors_and_submission_snapshot(runtime, monkeypatch, capsys):
    public = load_entrypoint("public")
    runtime.start(1)
    monkeypatch.setattr(public, "Runtime", lambda: runtime)

    def invoke(args, source):
        monkeypatch.setattr(public.sys, "argv", ["language-public", *args])
        stream = io.BytesIO(source)
        monkeypatch.setattr(public.sys, "stdin", SimpleNamespace(buffer=stream))
        public.main()
        return json.loads(capsys.readouterr().out), stream.tell()

    result, consumed = invoke(["compile", "problem-01"], b"a" * 20_000)
    assert result["error"].startswith("SOURCE_ERROR")
    assert consumed == 8193
    result, _ = invoke(["compile", "problem-01"], b"\xff")
    assert result["error"].startswith("SYNTAX_ERROR")
    result, _ = invoke(["submit", "problem-01"], b"invalid")
    assert result["score"] == 0
    assert set(result) == {"submission", "passed", "total", "score"}
    with pytest.raises(ValueError):
        invoke(["compile", "problem-01", "/opt/programming-language/trial.json"], b"")
    assert runtime.settle(1)["reward"] == 0


def test_admin_only_advances_once_and_refuses_agent_identity(runtime, monkeypatch):
    admin = load_entrypoint("admin")
    runtime.start(1)
    monkeypatch.setattr(admin, "Runtime", lambda: runtime)
    monkeypatch.setattr(admin, "restore_agent_log_access", lambda *_: None)
    monkeypatch.setattr(admin.pwd, "getpwnam", lambda _: SimpleNamespace(pw_gid=2000))
    monkeypatch.setattr(admin.os, "geteuid", lambda: 0)
    monkeypatch.delenv("SUDO_USER", raising=False)
    monkeypatch.setattr(admin.sys, "argv", ["admin.py", "settle", "1"])
    admin.main()
    assert runtime.load()["current"]["index"] == 2
    state = runtime.load()
    admin.main()
    assert runtime.load() == state
    monkeypatch.setenv("SUDO_USER", "agent")
    with pytest.raises(ValueError, match="harness"):
        admin.main()
    monkeypatch.delenv("SUDO_USER")
    monkeypatch.setattr(admin.os, "geteuid", lambda: 2000)
    with pytest.raises(ValueError, match="harness"):
        admin.main()
    assert runtime.load() == state
