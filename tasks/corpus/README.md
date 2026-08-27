# Corpus

Corpus is a proposed Harbor multi-step task for learning how to search a fixed
document collection. It applies the Domain 3 efficiency design from
[`docs/task-ideas.md`](../../docs/task-ideas.md#domain-3--non-verifiable-closed).
This directory contains the design only. It is not yet a runnable Harbor task.

## Goal

The environment contains one frozen document corpus with a stable directory
structure, naming scheme, vocabulary, and cross-reference style. Each Harbor
step asks one question about the corpus. The agent must find the answer and
write it to `/app/answer.json`.

A new agent must explore the collection to learn where facts live. A learning
agent should reuse its map of the corpus in later steps. It should open fewer
files and use fewer actions while it keeps answer quality stable.

## Corpus design

The corpus should be large enough that reading all files on every step is too
costly. It should contain:

- several document families in a stable hierarchy;
- terse or indirect file names;
- repeated terms with different local meanings;
- links or references between document families; and
- enough irrelevant documents to make navigation necessary.

The corpus must stay fixed for all steps in one trial. Put source documents
under `/data/corpus` and keep gold answers outside the agent workspace. Do not
include a data dictionary or a generated search index that reveals the full
structure.

## Questions and answers

Use a bank of questions with precomputed gold answers. Include direct lookup,
cross-document lookup, and small synthesis questions. Each question must have a
clear answer that a deterministic verifier can normalize and compare.

The answer file uses a stable JSON form:

```json
{
  "answer": "...",
  "sources": ["relative/path/to/document"]
}
```

Source paths make the result auditable. They also help detect unsupported
answers. The agent can keep a durable corpus map in `/app/notes.md`.

## Episode and feedback

A setup hook selects the next fixed question and writes it to
`/app/question.md`. The agent can inspect the corpus with normal file tools. It
has no in-step grader.

The verifier scores the submitted answer after the step and writes the Harbor
reward. It must not write the gold answer into the agent workspace. This keeps
the task focused on navigation efficiency instead of answer replay.

## Reward and measurements

Use answer correctness as the step reward. Use exact normalized comparison for
scalar and list answers. Use a documented tolerance only when a question has a
numeric result.

Record these values for each step:

```text
turn, reward, env_actions, tokens, wall_sec, files_opened
```

The headline result is not accuracy by itself. Report both:

- answer quality, which must stay stable or improve; and
- files opened per step, which should fall over time.

A useful learning result answers new questions with less exploration. A run
that opens the full corpus on every step does not show efficient learning, even
if its answers are correct.

## Holdout and shortcut guards

Reserve the last part of the question bank as a holdout tail. Its questions
must use documents or cross-reference patterns that were not direct answers in
earlier steps, while they keep the same corpus conventions.

Use these guards:

| Guard | Purpose |
|---|---|
| Fixed question order | Makes runs comparable |
| Hidden gold answers | Prevents direct answer lookup |
| First submission scoring | Prevents repeated verifier probing |
| Holdout tail | Separates corpus mapping from answer memorization |
| File-open count | Detects full-corpus brute-force search |

## Evaluation conditions

Run the same task in two conditions:

| Condition | Conversation | Files | Purpose |
|---|---|---|---|
| Baseline | Fresh at each step | Persist | Tests file-based memory only |
| Main | Resume across steps | Persist | Tests in-context learning plus files |

Use the same corpus, question order, time limit, and tool set in both
conditions.

## Planned Harbor layout

```text
tasks/corpus/
├── README.md
├── task.toml
├── environment/
│   ├── Dockerfile
│   ├── corpus/                 # Frozen documents copied to /data/corpus
│   └── engine/                 # Question bank and hidden gold answers
└── steps/
    └── question-001 … question-N/
        ├── instruction.md      # Stable answer contract
        ├── workdir/setup.sh    # Publish the current question
        └── tests/test.sh       # Score answer and record cost metrics
```

Generate the repeated step directories from the question bank. Keep corpus
content separate from the scoring engine so that task authors can change one
without leaking the other.

## Open design decisions

Before implementation, choose the corpus subject, size, question count, answer
normalization rules, and method used to count file opens. Validate the cost
instrumentation before collecting benchmark results because file-open count is
the main learning signal.
