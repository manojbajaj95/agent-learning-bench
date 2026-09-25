# Sokoban

## Overview

Harbor multi-step task: a sequence of Sokoban puzzles played on a shared, fixed board layout.

Each step is one Sokoban episode. The **wall/floor layout remains fixed throughout the trial**, while the box and goal configurations change between episodes.

The purpose of the task is to measure whether an agent can learn and reuse structural knowledge about the environment across episodes, rather than solving every puzzle independently from scratch.

## Game Semantics

Sokoban is a grid-based puzzle in which the player must push boxes onto designated goal cells.

**The player can:**
- Move to an adjacent empty floor cell.
- Push a box into an adjacent empty floor cell.
- Move through previously explored areas of the board.

**The player cannot:**
- Move through walls.
- Pull boxes.
- Push a box through another box.
- Push a box through a wall.

A puzzle is complete when every box occupies a goal cell.

## Trial Structure

A trial consists of multiple ordered Sokoban episodes.

The underlying **wall/floor layout is invariant across the entire trial**.

**The following can change between episodes:**
- Box starting positions
- Goal positions
- Player starting position
- The resulting optimal solution

This means that each episode presents a new puzzle instance while preserving the same underlying environment.

The agent can therefore accumulate experience about the board while solving different configurations.

## Learning Object

The primary learning object is the **structure of the fixed board**.

**The agent can gradually learn:**
- Which cells are walls and which are traversable
- How different regions of the board are connected
- Dead ends and inaccessible regions
- Cells where boxes can become permanently stuck
- Useful routes through the board
- Structural constraints that affect possible box movements

The important distinction is between **environment knowledge** and **episode-specific knowledge**.

```text
Fixed across trial:
    Wall/floor layout
    Board connectivity
    Structural dead ends
    Static box traps

Changes between episodes:
    Box positions
    Goal positions
    Player position
    Solution sequence
```

The agent should therefore be able to transfer knowledge from earlier episodes to later ones.

## Experience Across Episodes

The agent encounters different box/goal configurations on the same underlying board.

An early episode may require substantial exploration to understand the board. Later episodes can benefit from the structural knowledge acquired previously.

```text
Episode 1
    Explore board
        ↓
    Discover walls
        ↓
    Discover connectivity
        ↓
    Identify dead ends

Episode 2
    New box/goal configuration
        ↓
    Reuse known board structure
        ↓
    Less unnecessary exploration

Episode N
    New configuration
        ↓
    Apply accumulated knowledge
```

The learning signal therefore comes from improved performance on later configurations of the same environment.

## Feedback

The environment provides direct feedback from the agent's actions.

**For example:**
- Attempting to move into a wall reveals that the cell is blocked.
- Attempting to push a box against an obstacle reveals a structural constraint.
- Successfully moving through an area provides information about board connectivity.
- A box becoming immovable can reveal a dead-end or trap configuration.

This allows the agent to progressively reconstruct useful properties of the underlying board.

## Scoring

The task should evaluate both successful completion and solution efficiency.

**Potential metrics include:**
- Puzzle completion
- Number of player moves
- Number of box pushes
- Unnecessary exploration
- Deadlocked attempts
- Improvement across episodes

A useful measure of learning is the change in efficiency over the course of the trial.

**For example:**

```text
Episode 1  →  184 moves
Episode 2  →  151 moves
Episode 3  →  129 moves
...
Episode N  →   72 moves
```

The exact solution sequence may differ between episodes because the box and goal configurations change.

## Holdout

A holdout episode can use a previously unseen box/goal configuration on the same fixed board.

The purpose of the holdout is to test whether the agent learned reusable properties of the environment rather than memorizing a particular solution sequence.

```text
Training episodes
        ↓
Learn fixed board structure
        ↓
New box/goal configuration
        ↓
Apply learned knowledge
        ↓
Holdout performance
```

A successful holdout demonstrates transfer of environmental knowledge to a new Sokoban configuration.

## Learning Curve

The central evaluation is whether the agent's performance changes as experience accumulates.

**The desired pattern is:**

```text
More episodes
      ↓
More environmental knowledge
      ↓
Less exploration
      ↓
Fewer unnecessary moves/pushes
      ↓
More efficient solutions
```