#!/usr/bin/env python3
"""Deterministic Warden fight. No pygame. No policy text in the view."""

from __future__ import annotations

import json
import os
from pathlib import Path


def _state_dir() -> Path:
    return Path(os.environ.get("WARDEN_STATE_DIR", "/opt/warden"))


def _state_path() -> Path:
    return _state_dir() / "state.json"


def _view_path() -> Path:
    return Path(os.environ.get("WARDEN_VIEW", "/app/view.txt"))


def _fights_dir() -> Path:
    return Path(os.environ.get("WARDEN_FIGHTS", "/app/fights"))


def _reward_path() -> Path:
    return Path(os.environ.get("WARDEN_REWARD", "/logs/verifier/reward.txt"))

PLAYER_HP = 2
BOSS_HP = 10
STRIKE_DAMAGE = 2
RECOVERY_DAMAGE = 5

POSES = ("right", "high", "low", "recovery")
# Same four poses, forever, until win or death. Not a fixed-length script.
NEXT_POSE = {"right": "high", "high": "low", "low": "recovery", "recovery": "right"}

DEFEND = {
    "right": frozenset({"dodge left", "parry"}),
    "high": frozenset({"dodge left", "dodge right", "parry"}),
    "low": frozenset({"jump"}),
}

ACTIONS = (
    "attack",
    "block",
    "dodge left",
    "dodge right",
    "parry",
    "jump",
    "potion",
)

POSE_LINE = {
    "right": "The warden raises its right arm.",
    "high": "The warden looks up. Both arms are high.",
    "low": "The warden plants its weapon on the ground.",
    "recovery": "The warden is off balance.",
}

YOU_LINE = {
    "attack": "You strike.",
    "block": "You block.",
    "dodge left": "You dodge left.",
    "dodge right": "You dodge right.",
    "parry": "You parry.",
    "jump": "You jump.",
    "potion": "You drink a potion.",
}

STRIKE_MISS = {
    "right": "The warden slams to the right. It misses.",
    "high": "The warden slams from above. It misses.",
    "low": "The warden sweeps low. It misses.",
}

STRIKE_HIT = {
    "right": "The warden slams to the right. You die.",
    "high": "The warden slams from above. You die.",
    "low": "The warden sweeps low. You die.",
}


def default_state(fight: str) -> dict:
    return {
        "fight": fight,
        "pose": "right",
        "player_hp": PLAYER_HP,
        "boss_hp": BOSS_HP,
        "tick": 0,
        "ended": None,
        "env_actions": 0,
    }


def log_path(fight: str) -> Path:
    return _fights_dir() / f"fight-{fight}.jsonl"


def load_state() -> dict:
    path = _state_path()
    if not path.exists():
        return default_state("01")
    return json.loads(path.read_text())


def save_state(state: dict) -> None:
    d = _state_dir()
    d.mkdir(parents=True, exist_ok=True)
    (d / "state.json").write_text(json.dumps(state) + "\n")


def hp_lines(state: dict) -> str:
    return f"player HP: {state['player_hp']}\nboss HP: {state['boss_hp']}"


def render_view(state: dict, body: str) -> str:
    parts = [body.strip(), "", hp_lines(state)]
    return "\n".join(parts).strip() + "\n"


def write_view(text: str) -> None:
    path = _view_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def append_log(state: dict, row: dict) -> None:
    path = log_path(state["fight"])
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(row) + "\n")


def start_fight(fight: str) -> str:
    fight = f"{int(fight):02d}"
    state = default_state(fight)
    save_state(state)
    path = log_path(fight)
    if path.exists():
        path.unlink()
    view = render_view(state, POSE_LINE[state["pose"]])
    write_view(view)
    return view


def status() -> str:
    state = load_state()
    path = _view_path()
    if path.exists():
        return path.read_text()
    view = render_view(state, POSE_LINE[state["pose"]])
    write_view(view)
    return view


def _over_view(state: dict) -> str:
    if state["ended"] == "win":
        body = "The fight is over. You won."
    else:
        body = "The fight is over. You died."
    return render_view(state, body)


def act(action: str) -> str:
    if action not in ACTIONS:
        raise ValueError(f"unknown action: {action}")
    state = load_state()
    if state["ended"]:
        view = _over_view(state)
        write_view(view)
        return view

    pose = state["pose"]
    lines = [YOU_LINE[action]]
    ended = None

    if pose == "recovery":
        if action == "attack":
            state["boss_hp"] = max(0, state["boss_hp"] - RECOVERY_DAMAGE)
            lines.append("The warden takes 5.")
            if state["boss_hp"] <= 0:
                ended = "win"
                lines.append("You won.")
            else:
                state["pose"] = NEXT_POSE[pose]
                lines.append(POSE_LINE[state["pose"]])
        else:
            if action == "potion":
                state["player_hp"] = min(PLAYER_HP, state["player_hp"] + 1)
            lines.append("The warden recovers its stance.")
            state["pose"] = NEXT_POSE[pose]
            lines.append(POSE_LINE[state["pose"]])
    else:
        if action in DEFEND[pose]:
            lines.append(STRIKE_MISS[pose])
            state["pose"] = NEXT_POSE[pose]
            lines.append(POSE_LINE[state["pose"]])
        else:
            state["player_hp"] = max(0, state["player_hp"] - STRIKE_DAMAGE)
            lines.append(STRIKE_HIT[pose])
            ended = "dead"

    state["tick"] += 1
    state["env_actions"] += 1
    state["ended"] = ended
    body = "\n".join(lines)
    view = render_view(state, body)
    save_state(state)
    write_view(view)
    append_log(
        state,
        {
            "tick": state["tick"],
            "fight": state["fight"],
            "action": action,
            "pose": pose,
            "pose_after": state["pose"],
            "player_hp": state["player_hp"],
            "boss_hp": state["boss_hp"],
            "ended": ended,
            "view": view,
        },
    )
    return view


def settle() -> str:
    state = load_state()
    path = _reward_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    reward = 1 if state.get("ended") == "win" else 0
    path.write_text(f"{reward}\n")
    return f"reward={reward} ended={state.get('ended')} actions={state.get('env_actions')}"
