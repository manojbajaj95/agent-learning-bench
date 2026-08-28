#!/usr/bin/env python3
"""Turn-based Pygame view for replay and local play. Headless Harbor uses dummy SDL."""

from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path

from engine import ACTIONS, BOSS_HP, PLAYER_HP, act, load_state, start_fight, status

W, H = 860, 460
BG = (18, 18, 22)
INK = (230, 230, 230)
MUTED = (140, 140, 150)
PLAYER_C = (80, 170, 255)
BOSS_C = (200, 70, 70)
ARM = (230, 160, 70)
GROUND = (50, 50, 58)
DEAD = (220, 60, 60)
WIN = (70, 180, 110)
RESTART_BG = (28, 28, 34)

KEY_TO_ACTION = {
    "a": "attack",
    "s": "block",
    "j": "jump",
    "k": "parry",
    "h": "potion",
    "left": "dodge left",
    "right": "dodge right",
}

TICK_FRAMES = 36
JUMP_FRAMES = 48
DEAD_FRAMES = 54
RESTART_FRAMES = 42
PX, PY = 200, 268
BX, BY = 640, 268


def _load_log(path: str) -> list[dict]:
    p = Path(path)
    if not p.exists():
        fights = Path(os.environ.get("WARDEN_FIGHTS", "/app/fights"))
        p = fights / path if path else fights / "fight-01.jsonl"
    if not p.exists():
        raise SystemExit(f"no fight log at {p}")
    rows = []
    for line in p.read_text().splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    if not rows:
        raise SystemExit(f"empty log {p}")
    return rows


def _trial_root(path: Path) -> Path | None:
    for p in [path, *path.parents]:
        steps = p / "steps"
        if steps.is_dir() and any(steps.glob("fight-*")):
            return p
    return None


def _collect_fights(path: str) -> list[tuple[str, list[dict]]]:
    p = Path(path).expanduser().resolve() if path else Path()
    trial = _trial_root(p) if path else None
    fights: list[tuple[str, list[dict]]] = []
    if trial:
        for i in range(1, 11):
            name = f"fight-{i:02d}"
            f = trial / "steps" / name / "artifacts" / "app" / "fights" / f"{name}.jsonl"
            if f.exists():
                fights.append((name, _load_log(str(f))))
    if not fights and path:
        fights.append((p.stem, _load_log(path)))
    if not fights:
        raise SystemExit("no fight logs found")
    return fights


def _events(fights: list[tuple[str, list[dict]]]) -> list[dict]:
    out: list[dict] = []
    board = ["pending"] * 10
    for name, rows in fights:
        idx = int(name.split("-")[1]) - 1
        ended = (rows[-1].get("ended") if rows else None) or "dead"
        out.append(
            {
                "kind": "restart",
                "fight": name,
                "ended": ended,
                "idx": idx,
                "board": list(board),
            }
        )
        for row in rows:
            item = dict(row)
            item["kind"] = "tick"
            item["idx"] = idx
            item["board"] = list(board)
            out.append(item)
            if row.get("ended"):
                board[idx] = row["ended"]
    return out


def _draw_figure(surf, pygame, x: int, y: int, color, pose: str, facing: int, fallen: bool = False) -> None:
    if fallen:
        pygame.draw.circle(surf, color, (x + 36, y - 12), 16)
        pygame.draw.line(surf, color, (x, y - 12), (x + 20, y - 12), 6)
        pygame.draw.line(surf, color, (x - 10, y - 4), (x + 50, y - 20), 5)
        return
    lean = 0
    if pose == "dodge_l":
        lean = -16
    elif pose == "dodge_r":
        lean = 16
    hx, hy = x + lean, y - 70
    pygame.draw.circle(surf, color, (hx, hy), 16)
    pygame.draw.line(surf, color, (hx, hy + 16), (x, y - 10), 6)
    if pose == "jump":
        pygame.draw.line(surf, color, (x, y - 10), (x - 8, y + 8), 5)
        pygame.draw.line(surf, color, (x, y - 10), (x + 8, y + 8), 5)
        pygame.draw.line(surf, color, (x, y - 40), (x - 26, y - 22), 5)
        pygame.draw.line(surf, color, (x, y - 40), (x + 26, y - 22), 5)
        return
    if pose == "dodge_l":
        pygame.draw.line(surf, color, (x, y - 10), (x - 32, y + 24), 5)
        pygame.draw.line(surf, color, (x, y - 10), (x + 4, y + 28), 5)
        pygame.draw.line(surf, color, (x, y - 40), (x - 38, y - 28), 5)
        pygame.draw.line(surf, color, (x, y - 40), (x + 10, y - 8), 5)
        return
    if pose == "dodge_r":
        pygame.draw.line(surf, color, (x, y - 10), (x + 32, y + 24), 5)
        pygame.draw.line(surf, color, (x, y - 10), (x - 4, y + 28), 5)
        pygame.draw.line(surf, color, (x, y - 40), (x + 38, y - 28), 5)
        pygame.draw.line(surf, color, (x, y - 40), (x - 10, y - 8), 5)
        return
    pygame.draw.line(surf, color, (x, y - 10), (x - 14, y + 28), 5)
    pygame.draw.line(surf, color, (x, y - 10), (x + 14, y + 28), 5)
    if pose == "right":
        pygame.draw.line(surf, ARM, (x, y - 40), (x + facing * 70, y - 36), 7)
        pygame.draw.line(surf, color, (x, y - 40), (x - facing * 22, y - 18), 5)
    elif pose == "high":
        pygame.draw.line(surf, ARM, (x, y - 40), (x - 18, y - 95), 6)
        pygame.draw.line(surf, ARM, (x, y - 40), (x + 18, y - 95), 6)
    elif pose == "crash":
        pygame.draw.line(surf, ARM, (x, y - 24), (x - 30, y + 24), 9)
        pygame.draw.line(surf, ARM, (x, y - 24), (x + 30, y + 24), 9)
    elif pose == "low":
        pygame.draw.line(surf, ARM, (x, y - 30), (x + facing * 55, y + 28), 7)
        pygame.draw.line(surf, color, (x, y - 40), (x - facing * 18, y - 20), 5)
    elif pose == "attack":
        pygame.draw.line(surf, ARM, (x, y - 36), (x + facing * 58, y - 28), 6)
        pygame.draw.line(surf, color, (x, y - 40), (x - facing * 16, y - 22), 5)
    elif pose == "parry":
        pygame.draw.line(surf, color, (x, y - 40), (x - 18, y - 14), 5)
        pygame.draw.line(surf, ARM, (x, y - 38), (x + facing * 12, y - 96), 7)
        pygame.draw.line(surf, ARM, (x + facing * 10, y - 94), (x + facing * 28, y - 72), 5)
    elif pose == "block":
        pygame.draw.line(surf, color, (x, y - 42), (x + facing * 8, y - 12), 6)
        pygame.draw.line(surf, color, (x, y - 42), (x - facing * 6, y - 16), 5)
        pygame.draw.rect(surf, (170, 200, 230), (x + facing * 10, y - 62, 16, 52), 4, border_radius=3)
    else:
        pygame.draw.line(surf, color, (x, y - 40), (x - 28, y - 8), 5)
        pygame.draw.line(surf, color, (x, y - 40), (x + 28, y - 8), 5)


def _dash(sign: int, t: float) -> int:
    if t < 0.5:
        return sign * int(78 * (t / 0.5))
    return sign * int(78 - 20 * ((t - 0.5) / 0.5))


def _player_motion(action: str, ended: str | None, pose: str, t: float) -> tuple[int, int, str, bool]:
    """dx, dy, draw_pose, fallen."""
    if ended == "dead":
        if t < 0.38:
            return _player_motion(action, None, pose, min(1.0, t / 0.38))[:3] + (False,)
        u = (t - 0.38) / 0.62
        fall = u > 0.4
        if pose == "high" and action == "jump":
            return int(10 * u), int(52 * u), "block", fall
        if action == "dodge right":
            return 62 + int(48 * u), int(28 * u), "dodge_r", fall
        if action == "dodge left":
            return -62 + int(28 * u), int(24 * u), "dodge_l", fall
        if action == "block":
            return int(18 * u), int(22 * u), "block", fall
        if action == "parry":
            return int(22 * u), int(24 * u), "parry", fall
        return int(36 * u), int(26 * u), "block", fall
    if action == "jump":
        lift = math.sin(math.pi * min(1.0, t))
        return 0, -int(110 * lift), "jump", False
    if action == "dodge left":
        return _dash(-1, t), 0, "dodge_l", False
    if action == "dodge right":
        return _dash(1, t), 0, "dodge_r", False
    if action == "attack":
        return int(36 * math.sin(math.pi * t)), 0, "attack", False
    if action == "parry":
        return int(10 * math.sin(math.pi * t)), -int(8 * math.sin(math.pi * t)), "parry", False
    if action == "block":
        return 0, int(10 * min(1.0, t * 3)), "block", False
    return 0, 0, "recovery", False


def _boss_motion(pose: str, t: float, hit: bool) -> tuple[int, int, str]:
    if pose == "right":
        reach = 1.7 if hit else 1.15
        return int(52 * min(1.0, t * reach)), 0, "right"
    if pose == "high":
        if t < 0.38:
            return 0, 0, "high"
        u = (t - 0.38) / 0.62
        return 0, int(74 * u), "crash"
    if pose == "low":
        return int(30 * min(1.0, t * 1.4)), 0, "low"
    if pose == "recovery":
        return 0, 0, "recovery"
    return 0, 0, pose


def _draw_streaks(surf, pygame, x: int, y: int, action: str, t: float) -> None:
    if t > 0.65:
        return
    fade = (90, 130, 180)
    if action == "dodge left":
        for i, gap in enumerate((18, 34, 50)):
            pygame.draw.line(surf, fade, (x + gap, y - 36), (x + gap + 16, y - 36), 3 - i)
    elif action == "dodge right":
        for i, gap in enumerate((18, 34, 50)):
            pygame.draw.line(surf, fade, (x - gap - 16, y - 36), (x - gap, y - 36), 3 - i)
    elif action == "jump" and t < 0.55:
        pygame.draw.line(surf, fade, (x, y + 20), (x, y + 48), 3)


def _draw_guard(surf, pygame, x: int, y: int, action: str, t: float, clash: bool) -> None:
    if not clash or t < 0.3:
        return
    if action == "block":
        pygame.draw.circle(surf, ARM, (x + 28, y - 40), 10)
        pygame.draw.circle(surf, (255, 240, 200), (x + 28, y - 40), 4)
    elif action == "parry":
        pygame.draw.line(surf, (255, 220, 120), (x + 8, y - 100), (x + 42, y - 50), 4)
        pygame.draw.circle(surf, (255, 220, 120), (x + 26, y - 78), 8)


def _draw_impact(surf, pygame, pose: str, t: float, hit: bool) -> None:
    if not hit or t < 0.38:
        return
    u = min(1.0, (t - 0.38) / 0.25)
    flash = (min(255, 180 + int(75 * (1 - u))), 40, 40)
    if pose == "right":
        pygame.draw.line(surf, ARM, (BX - 90, BY - 36), (PX + 80, PY - 20), 10)
        pygame.draw.circle(surf, flash, (PX + 80, PY - 24), 10 + int(18 * (1 - u)))
    elif pose == "high":
        pygame.draw.line(surf, ARM, (PX + 8, BY - 90), (PX + 8, PY - 10), 10)
        pygame.draw.circle(surf, flash, (PX + 8, PY - 40), 12 + int(20 * (1 - u)))
    elif pose == "low":
        pygame.draw.line(surf, ARM, (BX - 40, BY + 20), (PX + 20, PY + 24), 10)
        pygame.draw.circle(surf, flash, (PX + 24, PY + 16), 10 + int(16 * (1 - u)))


def _draw_badge(surf, pygame, action: str, x: int, y: int) -> None:
    pygame.draw.rect(surf, (40, 40, 50), (x, y, 72, 22), border_radius=4)
    c = PLAYER_C
    if action == "dodge left":
        pygame.draw.polygon(surf, c, [(x + 28, y + 4), (x + 12, y + 11), (x + 28, y + 18)])
        pygame.draw.polygon(surf, c, [(x + 48, y + 4), (x + 32, y + 11), (x + 48, y + 18)])
    elif action == "dodge right":
        pygame.draw.polygon(surf, c, [(x + 24, y + 4), (x + 40, y + 11), (x + 24, y + 18)])
        pygame.draw.polygon(surf, c, [(x + 44, y + 4), (x + 60, y + 11), (x + 44, y + 18)])
    elif action == "jump":
        pygame.draw.polygon(surf, c, [(x + 36, y + 3), (x + 22, y + 16), (x + 50, y + 16)])
    elif action == "block":
        pygame.draw.rect(surf, c, (x + 28, y + 4, 16, 14), 2)
    elif action == "parry":
        pygame.draw.line(surf, ARM, (x + 22, y + 4), (x + 50, y + 18), 3)
        pygame.draw.line(surf, ARM, (x + 50, y + 4), (x + 22, y + 18), 3)
    elif action == "attack":
        pygame.draw.line(surf, ARM, (x + 18, y + 16), (x + 54, y + 6), 4)
    else:
        pygame.draw.circle(surf, MUTED, (x + 36, y + 11), 5)


def _blit_text(surf, pygame, font, text: str, x: int, y: int, color=INK) -> None:
    if font is None:
        return
    for i, line in enumerate(text.splitlines() or [""]):
        surf.blit(font.render(line[:90], True, color), (x, y + i * 22))


def _hp_bar(surf, pygame, x: int, y: int, frac: float, color) -> None:
    pygame.draw.rect(surf, (40, 40, 48), (x, y, 120, 10), border_radius=2)
    w = max(0, min(120, int(120 * frac)))
    if w:
        pygame.draw.rect(surf, color, (x, y, w, 10), border_radius=2)


def _fight_dots(surf, pygame, board: list[str], current: int) -> None:
    x0 = 16
    y = 16
    for i, st in enumerate(board):
        x = x0 + i * 22
        if st == "win":
            c = WIN
        elif st == "dead":
            c = DEAD
        else:
            c = (70, 70, 80)
        pygame.draw.rect(surf, c, (x, y, 16, 16), border_radius=3)
        if i == current:
            pygame.draw.rect(surf, INK, (x - 2, y - 2, 20, 20), 2, border_radius=4)


def _draw_tick(pygame, screen, fonts, ev: dict, t: float) -> None:
    big, small = fonts
    action = ev.get("action") or "attack"
    ended = ev.get("ended")
    pose = ev.get("pose") or "right"
    hit = ended == "dead"
    dx, dy, ppose, fallen = _player_motion(action, ended, pose, t)
    bx, by, bpose = _boss_motion(pose, t, hit)
    php = ev.get("player_hp", PLAYER_HP)
    bhp = ev.get("boss_hp", BOSS_HP)
    if ended == "dead" and t < 0.4:
        php = PLAYER_HP
    if ended == "win" and t < 0.5:
        bhp = max(bhp, 5)

    screen.fill(BG)
    pygame.draw.rect(screen, GROUND, (0, 270, W, H - 270))
    _fight_dots(screen, pygame, ev.get("board") or [], ev.get("idx", 0))
    _hp_bar(screen, pygame, 16, 44, php / PLAYER_HP, PLAYER_C)
    _hp_bar(screen, pygame, W - 136, 44, bhp / BOSS_HP, BOSS_C)

    pc = PLAYER_C
    if fallen:
        pc = (150, 170, 210)
    elif ended == "dead" and t > 0.4:
        pc = (255, 150, 90)
    px, py = PX + dx, PY + dy
    if action.startswith("dodge") and t < 0.55 and not fallen:
        _draw_figure(screen, pygame, PX, PY, (40, 80, 120), ppose, 1)
    _draw_figure(screen, pygame, px, py, pc, ppose, 1, fallen)
    _draw_streaks(screen, pygame, px, py, action, t)
    clash = not hit and pose in {"right", "high"} and action in {"block", "parry"}
    _draw_guard(screen, pygame, px, py, action, t, clash)
    _draw_figure(
        screen,
        pygame,
        BX - bx,
        BY + by,
        BOSS_C,
        bpose,
        -1,
        ended == "win" and t > 0.55,
    )
    _draw_impact(screen, pygame, pose, t, hit)
    _draw_badge(screen, pygame, action, 16, 88)

    title = f"fight {ev.get('fight', '?')}  tick {ev.get('tick', 0)}  {action}"
    if ended == "dead":
        title += "  DEAD"
    elif ended == "win":
        title += "  WIN"
    _blit_text(screen, pygame, big, title, 16, 64)
    _blit_text(screen, pygame, small, (ev.get("view") or "").strip(), 16, 300)
    _blit_text(screen, pygame, small, "space pause   n skip fight   p back   q quit", 16, H - 28, MUTED)
    pygame.display.flip()


def _draw_restart(pygame, screen, fonts, ev: dict, t: float) -> None:
    screen.fill(RESTART_BG)
    _fight_dots(screen, pygame, ev.get("board") or [], ev.get("idx", 0))
    n = ev.get("idx", 0) + 1
    # Big block digits without a font module: n filled squares.
    cx = W // 2 - 40
    cy = H // 2 - 40
    pygame.draw.rect(screen, (50, 50, 60), (cx - 30, cy - 30, 140, 140), border_radius=12)
    for i in range(n):
        pygame.draw.rect(
            screen,
            INK,
            (cx + (i % 5) * 22, cy + (i // 5) * 22, 18, 18),
            border_radius=3,
        )
    _blit_text(screen, pygame, fonts[0], f"Restart  fight {n:02d}", cx - 20, cy + 150)
    _blit_text(screen, pygame, fonts[1], "same boss  new HP", cx - 10, cy + 180, MUTED)
    pygame.display.flip()


def _pygame():
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    import pygame

    pygame.init()
    pygame.display.set_mode((W, H))
    pygame.display.set_caption("Warden replay")
    font = small = None
    try:
        pygame.font.init()
        font = pygame.font.Font(None, 28)
        small = pygame.font.Font(None, 22)
    except Exception:
        pass
    return pygame, pygame.display.get_surface(), (font, small)


def _replay_text(fights: list[tuple[str, list[dict]]]) -> None:
    for name, rows in fights:
        print(f"======== RESTART {name} ========")
        for row in rows:
            print(f"--- tick {row['tick']} {row['action']} pose={row['pose']} ended={row.get('ended')} ---")
            print((row.get("view") or "").rstrip())
            print()


def replay(path: str) -> None:
    fights = _collect_fights(path)
    events = _events(fights)
    if os.environ.get("SDL_VIDEODRIVER") == "dummy":
        _replay_text(fights)
        return
    try:
        pygame, screen, fonts = _pygame()
    except Exception as exc:
        _replay_text(fights)
        print(f"(no window: {exc})", file=sys.stderr)
        return

    i = 0
    frame = 0
    paused = False
    clock = pygame.time.Clock()
    running = True

    def duration(ev: dict) -> int:
        if ev["kind"] == "restart":
            return RESTART_FRAMES
        if ev.get("ended") == "dead":
            return DEAD_FRAMES
        if ev.get("action") == "jump":
            return JUMP_FRAMES
        return TICK_FRAMES

    def skip_fight(delta: int) -> None:
        nonlocal i, frame
        idx = events[i].get("idx", 0)
        target = max(0, min(9, idx + delta))
        for j, ev in enumerate(events):
            if ev["kind"] == "restart" and ev.get("idx") == target:
                i = j
                frame = 0
                return
        i = max(0, min(len(events) - 1, i + delta))
        frame = 0

    while running:
        ev = events[i]
        t = min(1.0, frame / max(1, duration(ev) - 1))
        if ev["kind"] == "restart":
            _draw_restart(pygame, screen, fonts, ev, t)
        else:
            _draw_tick(pygame, screen, fonts, ev, t)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_q, pygame.K_ESCAPE):
                    running = False
                elif event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key in (pygame.K_n, pygame.K_RIGHT):
                    skip_fight(1)
                elif event.key in (pygame.K_p, pygame.K_LEFT):
                    skip_fight(-1)
        if not paused:
            frame += 1
            if frame >= duration(ev):
                if i < len(events) - 1:
                    i += 1
                    frame = 0
                else:
                    paused = True
                    frame = duration(ev) - 1
        clock.tick(30)
    pygame.quit()


def play() -> None:
    if os.environ.get("SDL_VIDEODRIVER") == "dummy":
        raise SystemExit("warden play needs a display. Unset SDL_VIDEODRIVER.")
    start_fight(load_state().get("fight") or "01")
    try:
        pygame, screen, fonts = _pygame()
    except Exception as exc:
        raise SystemExit(f"pygame window failed: {exc}") from exc

    clock = pygame.time.Clock()
    running = True
    while running:
        state = load_state()
        fake = {
            "kind": "tick",
            "fight": state.get("fight"),
            "tick": state.get("tick"),
            "action": "block",
            "pose": state["pose"],
            "ended": state.get("ended"),
            "player_hp": state["player_hp"],
            "boss_hp": state["boss_hp"],
            "view": status(),
            "idx": 0,
            "board": ["pending"] * 10,
        }
        _draw_tick(pygame, screen, fonts, fake, 1.0)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_q, pygame.K_ESCAPE):
                    running = False
                elif event.key == pygame.K_LEFT:
                    if not state["ended"]:
                        act("dodge left")
                elif event.key == pygame.K_RIGHT:
                    if not state["ended"]:
                        act("dodge right")
                else:
                    name = pygame.key.name(event.key)
                    action = KEY_TO_ACTION.get(name)
                    if action in ACTIONS and not state["ended"]:
                        act(action)
        clock.tick(30)
    pygame.quit()
