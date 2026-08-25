# Agent Learning Bench

'We define AGI as a system that can match the learning efficiency of humans.' - Arc Prize

Models have gotten better, smarter, cheaper and faster but one missing piece is learning.

The goal of the benchmark is to build set of tasks to test agents capability to learn over time across runs.
Currently the closest benchmark we have is ARC-AGI3, which is still unsaturated and most models with default harness perform terribly bad.
Some newer solutions exist that are doing significantly better. See more: https://arcprize.org/leaderboard/community

There are still a few main concerns with the benchmark, primarily 'When a benchmark becomes a target, it seizes to become a good benchmark`
1. Short horizon tasks - For eg task, https://arcprize.org/tasks/ar25 has only 8 levels, meaning simple solution like [append only log](https://github.com/alexisfox7/PRO-LONG/tree/main) do very well 
2. Lack of variety - All the task environments are very similar in nature and do not test generalizability of learning
3. Benchmaxed - A lot of learning systems have been over fitted to arc-agi-3

## Contribution Guidelines

Build your task in Harbor format and submit it through the GitHub repository

## References

1. https://www.harborframework.com/docs
2. https://docs.arcprize.org/