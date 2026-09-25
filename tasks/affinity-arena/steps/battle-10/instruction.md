# Affinity Arena

Read `/app/world/RULES.md` and `/app/view.txt`.

Draft three creatures in order with `affinity-arena draft`, then use
`affinity-arena attack <move>` or `affinity-arena switch <creature>` until
the battle is over. `affinity-arena status` shows the current view for free.

Prioritize finishing the battle. After the initial reads, draft promptly;
then make a game action after each brief decision. Use known matchups and
learn unknown ones by playing. Do not enumerate complete affinity charts,
build exhaustive search solvers, install packages, or repeatedly reread logs.
Keep reasoning brief. If a helper is necessary, run it with `timeout 5`;
if it times out, abandon that computation and play the next action.

Update `/app/affinity-chart.json` with observed multipliers only, as
`{"attack affinity": {"defender affinity": 2}}`. Leave out unknown cells.
You can create helper files in `/app/workspace/`.

Save observed chart entries once the battle ends, then stop.
Do not try to restart it.
