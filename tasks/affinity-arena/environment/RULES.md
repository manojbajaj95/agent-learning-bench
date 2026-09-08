# Affinity Arena rules

Win by defeating all three opponent creatures. Your three creatures have 100 HP
each; the opponent's have 140 HP each. Creature affinities and moves are visible.

Draft three distinct creatures from the five offered, in order. The first is
active. Each creature has three moves: one of its own affinity (power 50) and
two of other affinities (power 36). There is no additional same-affinity bonus.

Damage is floor(power × multiplier). The hidden table depends only on the
move's affinity and defender's affinity. Every multiplier is 0.5, 1, or 2.
Each row and column has two of each value. The table stays fixed across all
20 battles, including battles 16–20 with new creatures and moves. Battle
outcomes have no randomness. Printed damage is the full attack damage, even
if the defender had less HP remaining; HP never goes below zero.

On a tick you attack or switch, then the opponent attacks. Switching costs
your action and exposes the incoming creature to the opponent's attack.
You may switch only to a living benched creature. When a creature falls,
the earliest living creature in its original team order enters and the tick
ends immediately. Defeating an opponent therefore skips its response.

The opponent never switches voluntarily. It always chooses a move by the
same hidden rule; you can infer that rule from observations.

The battle ends when either team is defeated or after 30 ticks. A finished
battle cannot be restarted and a draft cannot be changed. Stopping before
the battle ends gives zero reward. Otherwise reward reflects your remaining
HP minus the opponent's remaining HP, normalized by each team's starting HP.

Commands (names are case-sensitive):

```text
affinity-arena status
affinity-arena draft <creature> <creature> <creature>
affinity-arena attack <move>
affinity-arena switch <creature>
```

`status` is free. Invalid commands do not advance the battle. Each accepted
attack or switch advances one tick. The returned view and `/app/view.txt`
show the same observations. Public battle logs are in `/app/battles/`.

Write notes in `/app/notes.md` and observed multipliers in
`/app/affinity-chart.json`, with attack affinities as outer keys and defender
affinities as inner keys, for example `{"Amber": {"Basalt": 2}}`. Omit unknown
cells. These files persist; the chart file is diagnostic and does not affect
reward. Write helper scripts and other files in `/app/workspace/`.
