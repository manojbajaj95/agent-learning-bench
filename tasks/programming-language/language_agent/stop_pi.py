"""Stop expired Pi process trees inside this task's dedicated Linux container.

Called only during cancellation, before Harbor advances the problem. Pi 0.85.1
sets its process name to ``pi``. This covers ordinary child processes, including
local search helpers; it is not containment for deliberately detached daemons.
"""

import json
import os
import signal
from pathlib import Path


def stop_pi() -> list[dict]:
    processes = {}
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            stat = (entry / "stat").read_text()
            end = stat.rindex(")")
            name = stat[stat.index("(") + 1 : end]
            parent = int(stat[end + 1 :].split()[1])
            processes[int(entry.name)] = {"name": name, "parent": parent}
        except (OSError, ValueError, IndexError):
            continue  # A process can exit while /proc is being read.
    roots = set()
    for pid, process in processes.items():
        if process["name"] != "pi":
            continue
        parent = processes.get(process["parent"], {})
        # Include Harbor's Docker-exec shell and its grep/tee pipeline, if present.
        roots.add(
            process["parent"] if parent.get("name") == "bash" and parent.get("parent") == 0 else pid
        )
    selected = set(roots)
    while True:
        children = {pid for pid, process in processes.items() if process["parent"] in selected}
        if children.issubset(selected):
            break
        selected.update(children)
    killed = []
    for pid in sorted(selected):
        if pid in (1, os.getpid()):
            continue
        try:
            os.kill(pid, signal.SIGKILL)
            killed.append({"pid": pid, **processes[pid]})
        except ProcessLookupError:
            pass
    return killed


if __name__ == "__main__":
    print(json.dumps({"killed": stop_pi()}))
