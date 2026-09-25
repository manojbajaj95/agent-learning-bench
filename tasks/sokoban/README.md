# Sokoban

The agent solves several Sokoban puzzles on one fixed wall layout. Later puzzles should take fewer wasted moves. This directory is a design only. It has no `task.toml`. `alb prepare sokoban` rejects it.

## Task type

Verifiable. A move into a wall fails at once. A blocked push fails at once. The agent can choose another move in the same puzzle.

## Labels

`fixed`, `ordered`. The wall layout stays the same on every run. Episode order is the curriculum.

## Environment

Planned container:

- One wall and floor layout for the whole trial
- Box positions, goal positions, and the player start can change each episode
- The agent sees the board cells it has entered and the failures of illegal moves
- Hidden solution data stays outside `/app`
- Notes stay in `/app` and persist across episodes

The player can move to an empty floor cell and can push one box into an empty floor cell. The player cannot pull a box, push a box through a wall, or push a box through another box. The puzzle is complete when every box is on a goal.

## Step design

One trial is an ordered list of episodes. One step is one episode. The wall layout stays fixed. The box plan, the goals, and the player start change.

The holdout is a new box and goal plan on that same layout. It checks transfer of the board, not memory of one solution.

Episode count, board size, and the exact holdout split are not chosen yet.

## Learning goal

The learning object is the fixed board: walls, connections, dead ends, and cells where a box gets stuck. Moves and pushes should fall toward the optimum while completion stays high. Baseline starts a fresh chat each episode. In-context learning resumes the same chat.

## Reward and cost

The reward is not implemented. Each episode should score completion and efficiency. Record:

```text
turn, reward, solved, moves, pushes, deadlocks, optimal_moves, tokens, wall_sec
```

`reward` should rise when the puzzle is solved in fewer moves than the action budget. A timeout or a deadlock scores 0. `tokens` and `wall_sec` come from the Harbor job. The learning curve is moves and pushes falling across episodes, including the holdout.
