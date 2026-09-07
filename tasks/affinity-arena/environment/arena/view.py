"""The entire public observation surface; never accepts a chart or oracle."""

from .engine import AFFINITIES, Creature, Matchup, State, outcome


def creature_line(creature: Creature, hp: int, maximum: int, active: bool = False) -> str:
    moves = "  ".join(f"{m.name} ({AFFINITIES[m.affinity]} {m.power})" for m in creature.moves)
    return f"{'>' if active else ' '} {creature.name:<9} {AFFINITIES[creature.affinity]:<7} HP {hp}/{maximum}  {moves}"


def render(
    index: int,
    matchup: Matchup,
    team: tuple[Creature, ...],
    state: State,
    events: list[dict],
    ended: str | None = None,
) -> str:
    phase = ended or outcome(state) or (f"tick {state.tick}" if team else "draft")
    lines = [f"Affinity Arena — battle {index} of 20 — {phase}", "", "Opponent's team"]
    for i, creature in enumerate(matchup.opponent):
        hp = 0 if i < state.enemy else state.enemy_hp if i == state.enemy else 140
        lines.append(creature_line(creature, hp, 140, i == state.enemy))
    lines.extend(["", "Your team" if team else "Offered to you (draft three, in order)"])
    for i, creature in enumerate(team or matchup.offered):
        lines.append(
            creature_line(
                creature,
                state.hp[i] if team else 100,
                100,
                bool(team) and i == state.active and state.hp[i] > 0,
            )
        )
    if events:
        last = events[-1]
        lines.extend(["", f"Last action: {last['command']}"])
        for hit in last.get("hits", []):
            lines.append(
                f"  {hit['attacker']} used {hit['move']} ({AFFINITIES[hit['attack_affinity']]}) "
                f"on {hit['defender']} ({AFFINITIES[hit['defender_affinity']]}): {hit['damage']} damage."
            )
    if ended or outcome(state):
        lines.extend(["", f"Battle over: {ended or outcome(state)}."])
    elif not team:
        lines.extend(["", "Draft: affinity-arena draft <a> <b> <c>"])
    return "\n".join(lines) + "\n"
