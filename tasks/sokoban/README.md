# Sokoban

## Short Brief

A persistent, partially observable Sokoban task designed to evaluate whether an agent can learn from experience across multiple episodes.

The Sokoban board remains fixed throughout a trial: walls, boxes, and goals do not change. The player's starting position changes between episodes. The agent has a limited action budget and observes only the local region around its current position.

The task measures whether experience from earlier episodes helps the agent make better decisions and solve later episodes more efficiently.

## Verifiable / Non-Verifiable

**Verifiable**

The environment can deterministically verify:

- Whether the puzzle was solved.
- The number of actions taken.
- Whether the action limit was exceeded.

**Non-verifiable**

The task does not directly verify what the agent internally remembers or how it represents its experience. Learning is evaluated through changes in behavior and performance across episodes.

## Environment

The environment contains a single fixed Sokoban board with:

- Fixed wall positions.
- Fixed box positions.
- Fixed goal positions.
- A fixed board layout and game rules.
- A player whose starting position changes between episodes.

The board configuration remains unchanged throughout the trial.

The agent receives only a local observation around its current position rather than the complete board. This requires the agent to discover the environment through interaction.

## Step Design

Each step corresponds to one episode of the same Sokoban environment.

Across episodes:

- The underlying board remains unchanged.
- The player's starting position changes.
- The agent has a limited number of actions.
- The agent receives local observations as it moves.
- The agent can use experience from previous episodes when making decisions in later episodes.

The episodes are ordered so that experience can accumulate over time, but later episodes are not simply copies of earlier episodes.

A later episode may require the agent to revisit situations it encountered previously, allowing previously acquired knowledge to affect its decisions.

## Learning Goal

The goal is to determine whether the agent can use experience accumulated from previous episodes to improve its subsequent behavior.

Experience consists of relationships between situations, actions, and outcomes. For example, if the agent pushes a box against a wall and observes that the box does not move, repeatedly attempting the same push is unnecessary. When the agent encounters the same or a structurally similar situation later, it can use that previous experience to choose a different action.

Through repeated interaction, the agent may learn:

- Which actions are ineffective in particular situations.
- Which box movements lead to useful or undesirable states.
- Which areas of the board are dead ends or useful routes.
- Which previously discovered actions or sub-solutions can be reused.

The task therefore evaluates **behavioral reuse of experience**, rather than whether the agent explicitly records notes or uses a particular learning mechanism.

## Reward and Cost Metrics

The primary reward measures whether the episode is successfully solved.

- **Reward:** `1` if the puzzle is solved, otherwise `0`.
- **Cost:** the number of actions used during the episode.

A successful episode can therefore become cheaper over time as the agent gains experience.

For example:

```text
Episode 1:  Solved — 150 actions
Episode 2:  Solved — 121 actions
Episode 3:  Solved —  96 actions
Episode 4:  Solved —  74 actions
