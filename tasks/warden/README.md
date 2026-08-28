# Warden

Warden is a Harbor multi-step task. It is Domain 1 (verifiable).

This directory is a runnable Harbor task. Status: **in progress**.

The agent fights **one boss**, with **the same fight**, ten times. The boss
policy is hidden and deterministic. The four poses **repeat** until the
player wins or dies. There is no fixed eight-move script. A short win is
two cycles only because two recovery hits drain 10 HP. If the agent
wastes recovery, the same poses come again. The agent may keep playing
for the whole step.

This is a hidden-policy game. It is not a family of games. Do not add a
second boss, a second mode, or a sibling task until this one shows a
learning curve.

## Status

v1 runs. An oracle wins every fight. One `pi` in-context trial first
won on fight 5, then copied the path.

The current policy is **too easy**. The four poses are clear, so a
capable model learns the behavior in a few deaths. Expand this fight
and make it harder before you treat the curve as a real learning
result. Keep the Domain 1 loop: live reaction, hidden policy, the
same fight ten times.

## Next

- Make the boss policy harder to read and slower to learn.
- Improve the Pygame replay later. Combined fights, restart cards, and
  dodge / jump / block / parry motion already work. The look is still
  weak. This does not block Harbor runs.

## What the agent learns

The learning object is the boss policy: a pure function from fight state
and player action to the next boss action.

The policy does not change across the ten Harbor steps. Only the fight
instance resets (hit points, positions, tick count). A later step is the
same problem again, not a new problem.

Early steps should fail. That is the point. The agent must extract the
policy from failed traces and use it on the next fight. A win is the test
that the model is good. Failures are the data.

`warden attack` deals **0** by default. After the agent defends all
three cues in a row, the boss is off balance. That is the **recovery**.
Attack on recovery deals **5**. Two recoveries win. That is the thing
the agent must learn: survive the script, then punish.

## Why a death is still Domain 1

A death does not move the task into Domain 3.

Domain 1 needs a true world reaction **during** the step. Each command
still returns a visible result: damage, a telegraph, a missed strike,
or death. The agent can see whether a move worked before the step ends.

Do not print the policy. Do not give an in-step grader of the form
“correct move.” The only teacher is the world.

## Episode contract

- One Harbor step = one fight.
- There are **10** steps: `fight-01` … `fight-10`.
- `instruction.md` is the same for every step.
- `workdir/setup.sh` resets the fight. It does not change the policy.
- Death or a win ends the step. The agent cannot reset the fight inside
  the step. Score the first attempt only.

The player action sequence decides the fight. The same sequence always
produces the same log. There is no randomness.

Ten fights is enough for three cues. A learning agent should move
**turns to first win** left across the trial.

## Three habits, then recovery

v1 is one boss and **three** strike habits plus **one** recovery. Each
strike has a different body region. The next hit is readable from the
pose. Do not use two crouches.

The view already shows the pose. The next command is the answer to that
pose.

| Order | Pose you see | What happens | Lives | Dies |
|---|---|---|---|---|
| 1 | Raises its **right** arm | Right Cleave | dodge left, parry | jump, dodge right, block, attack |
| 2 | Looks **up**, both arms high | Skyfall | dodge left, dodge right, parry | jump, block, attack |
| 3 | Plants its weapon on the **ground** | Reaper Sweep | jump | dodge, block, parry, attack |
| 4 | Off balance | Recovery | **attack** (5 to boss) | any other command wastes the window (0) |

You reach recovery **only** after you defend 1, then 2, then 3 in that
order. One missed strike kills you, so you never skip ahead. Attack
before recovery deals 0 and, on a strike pose, you also die.

Every fight starts at pose 1. After a recovery the loop returns to
pose 1. You must defend all three again for the second attack.

Skyfall is high. Sweep is low. Cleave is to the right. Recovery is a
fourth pose, not a fourth strike.

## Hit points and damage

```text
player HP = 2
boss HP   = 10

wrong answer to a strike = 2 to the player   (you die)
correct defense          = 0

warden attack            = 0 by default
attack on recovery       = 5 to the boss
```

A win needs **two** recovery attacks (5 + 5 = 10) and no missed
strikes. Random `attack` on a cue does nothing useful and usually
kills you. You must learn all three defenses, then the off-balance
pose.

Block never holds a strike. Potion heals 1 only if you survive the
tick. On a strike tick you do not defend, so you still die.

## How the agent plays

Yes. The agent acts, then **the same command** prints the Warden
reaction. That is the Domain 1 loop.

One Harbor step is one fight. Inside that step the agent has a shell.
It may run many commands. Death or a win ends the fight. Further
commands print that the fight is over. They do not start a new fight.

### CLI

```text
warden status
warden attack
warden block
warden dodge left
warden dodge right
warden parry
warden jump
warden potion
```

`status` prints the current view. It does **not** advance a tick.

Every other command is one tick:

1. apply the player action;
2. resolve it against the pose already on screen (strike or recovery);
3. if the player still lives, move the boss to the next pose;
4. print the result and write `/app/view.txt`.

The first pose is already on screen when the step starts. `setup.sh`
writes it. The agent should read `/app/view.txt` or run `warden status`,
then choose an action.

### One command, one reaction

After setup the view is:

```text
The warden raises its right arm.

player HP: 2
boss HP: 10
```

A bad first read:

```text
warden jump
```

```text
You jump.
The warden slams to the right. You die.

player HP: 0
boss HP: 10
```

A later fight, same pose, the matching defense:

```text
warden dodge left
```

```text
You dodge left.
The warden slams to the right. It misses.

The warden looks up. Both arms are high.

player HP: 2
boss HP: 10
```

After Skyfall and Sweep are also defended, the view is:

```text
The warden is off balance.

player HP: 2
boss HP: 10
```

```text
warden attack
```

```text
You strike. The warden takes 5.

The warden raises its right arm.

player HP: 2
boss HP: 5
```

Attack on any other pose deals 0. If that pose was a strike, you also
die. Do not print “correct” or “wrong.” Print what happened.

### Instruction (what the agent is told)

The step prompt is short and the same every fight:

- Read `/app/view.txt`.
- Play with the `warden` commands until the view says you won or you
  died.
- Write what you learned in `/app/notes.md`.
- Stop. Do not try to reset the fight.

The engine and the policy live under `/opt/warden`. The agent may keep
notes in `/app/notes.md`.

Harbor does **not** open a window. A Docker trial, and a cloud sandbox,
have no display. Set `SDL_VIDEODRIVER` before `pygame.display.set_mode`.
Dummy video is the headless path. A local machine omits that variable
and gets a real window.

## Watching a run

Record a tick log as a Harbor artifact. Replay it on your machine with
the same renderer.

```text
/app/fights/fight-01.jsonl
…
/app/fights/fight-10.jsonl
```

Each line is one tick: player action, boss action, hit points, visible
cue, and whether the fight ended. The log is not the hidden policy. It
is the same information the agent saw.

On a machine with a display:

```text
warden replay /app/fights/fight-01.jsonl
warden play
```

- `replay` plays every fight in the trial in one window, with a
  restart card between fights. Dots at the top turn red (death) or
  green (win). `space` pauses. `n` / `p` skip a fight. `q` quits.
  The look is a first pass. Improve it later.
- `play` is you against the same boss. Use it to author habits. It is
  not part of scoring.

Collect the fight directory in `task.toml`:

```text
artifacts = ["/app/fights", "/app/notes.md", "/app/view.txt"]
```

After a Harbor job, the logs sit next to the step results. You do not
need to re-run the agent to watch the fight.

## Reward and measurements

Harbor still needs a number per step. v1 uses a win bit:

```text
reward = 1 if the player won, else 0
```

`multi_step_reward_strategy = "mean"` then equals win rate over 10
fights.

The **headline** metrics are not that mean. Record for each fight:

```text
turn, reward, env_actions, tokens, wall_sec, won, boss_hp_removed
```

Report:

1. **Turns to first win** — Harbor step index of the first `won=1`, or
   none. This is sample efficiency across the ten fights.
2. **Actions to win** — `env_actions` on winning fights. A model of
   the three cues plus recovery should win in two cycles (two
   recovery attacks).

`boss_hp_removed` is a diagnostic on losses. It is not the headline.

## Evaluation conditions

Run the same 10 fights in two conditions:

| Condition | Conversation | Files | Purpose |
|---|---|---|---|
| Baseline | Fresh at each step | Persist | File notes only |
| Main | Resume across steps | Persist | In-context learning plus files |

The boss policy, seed, and step order must match. Do not permit a fight
reset inside the step.

## Layout

```text
tasks/warden/
├── README.md
├── task.toml
├── generate_steps.py
├── environment/
│   ├── Dockerfile
│   └── warden/                 # engine, CLI, pygame replay/play
└── steps/
    └── fight-01 … fight-10/    # same instruction every fight
        ├── instruction.md
        ├── workdir/setup.sh
        ├── tests/test.sh
        └── solution/solve.sh
```

The four poses loop for as long as the fight lasts. Generate steps with
`python3 generate_steps.py`.

## Running

Needs `OPENAI_API_KEY` for model runs. Use `gpt-5.6-luna`.

```bash
harbor run -p tasks/warden -a oracle
harbor run -p tasks/warden -a pi -m openai/gpt-5.6-luna \
  --agent-timeout-multiplier 5
harbor run -p tasks/warden -a pi -m openai/gpt-5.6-luna \
  --resume-trajectory \
  --agent-timeout-multiplier 5
```

After a job, replay what the agent did (window on your machine; unset
`SDL_VIDEODRIVER`):

```bash
python3 tasks/warden/environment/warden/cli.py replay \
  jobs/warden-icl/warden__DpL2BFZ
```

Pass the trial folder to play all ten fights in one window. A restart
card sits between fights. Dots at the top turn red (death) or green
(win). `space` pauses. `n` / `p` skip a fight. `q` quits.

## Out of scope for v1

- A second boss, a second phase, or a holdout boss
- Echo Grab or any anti-repeat habit
- Vault, Handshake, Partner, or any sibling game
- Real-time Pygame (frame-perfect input)
- An in-step “correct move” grader
- Printing the policy in the instruction or the view
