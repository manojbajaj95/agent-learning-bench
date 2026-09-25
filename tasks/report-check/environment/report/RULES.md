# Northwind Ledger — Reporting Desk

Northwind Ledger is a back-office payments firm. It runs settlement,
reconciliation, treasury and onboarding for account holders across a merchant
book. The reporting desk publishes every report the firm issues.

## How the desk works

Each job arrives as a brief in `/app/brief.md`. The brief carries the report
type, the subject, the period, a job number and the source material. The source
material is written in plain language by whoever ran the work. It is **not**
written in house style.

You turn the source material into a finished report at `/app/report.md`, then
submit it:

```text
report submit
```

A reviewer reads the report and either accepts it or returns it with the
corrections it needs. Fix the file and submit again. `report status` shows how
many submissions are left on the current job.

## The house style guide

Northwind Ledger keeps a written house style guide. It is held by the reviewer
and it is not published to writers. Reviewers do not send out the guide, and
they do not summarise it on request. They return corrections on the report in
front of them, and nothing else.

## What the desk cares about

Reports go to account holders, auditors and the board. They must read the same
way whoever wrote them: the same shape, the same words for the same things, the
same way of setting out figures and dates, and no more length than the subject
needs. A report that says the right thing in the wrong form is returned.
