# CI Wait Workflow

Waiting on CI or automated review is a different phase of development — keep
advancing work instead of watching the check run.

## 1. Purpose

Use this optional playbook after a branch or pull request has entered CI or
automated review. The goal is to use the wait without weakening the evidence
from the checks or inventing new scope.

The rules below are textual expectations, not enforced policy. They do not
grant authority, change an actor's lane, or replace repository instructions.

## 2. Same PR safe defaults

Start with the work already under review:

- Read the complete diff as a reviewer would.
- Check names, comments, docs, and error paths for consistency.
- Run relevant local checks while healthy CI continues on the current tip.
- Prepare handoff notes and verification evidence without changing the tip.

**Mechanical CI** means a formatter, linter, or unit-test failure on the current
tip that is reproducible locally and has one obvious correction which does not
change architecture, security, scope, dependencies, authorization, or intended
behavior.

**Rule 2 — Do not push speculatively during healthy CI.** Push only a confirmed,
current-tip Mechanical CI fix. A push supersedes the running checks, so do not
discard useful in-flight evidence for cleanup, guesses, or unrelated changes.

For flaky or unrelated CI, re-run only when allowed or escalate; do not expand
scope.

**Example — current-tip mechanical fix.** A formatter or unit test fails on the
tip, the failure reproduces locally, and the narrow correction passes locally.
Commit that mechanical fix and make a superseding push, then follow the new tip.

## 3. Parallel work on another branch

**Rule 1 — Parallel work requires prior authority.** Work on task B only when it
was already assigned or explicitly authorized. Review task C only when the
actor's lane permits that review.

Keep authorized task B on its own branch and worktree. Do not mix its commits,
files, or acceptance evidence into waiting task A.

If neither parallel work nor review is authorized, prepare the handoff, perform
read-only context gathering, or stop. A CI wait never creates a follow-on task.

**Example — authorized task B.** Task B was assigned before task A entered CI.
While A's checks run, create or resume B's separate branch, work only within
B's brief, then return to A when its checks complete.

## 4. If waits stay long (advice only)

Repeated long waits may justify a separate CI improvement task. Possible ideas
include running fast linters first, improving safe cache use, or splitting jobs
so failures arrive sooner.

Treat those ideas as input to later planning. Do not edit workflows, reorder
required checks, or tune infrastructure from the waiting PR unless that CI work
has its own approved scope.

## 5. Cadence

1. Put task A into CI or automated review and record its exact tip.
2. Use the same-PR safe defaults while A is healthy and pending.
3. Move to authorized task B, or permitted review C, only within existing
   authority.
4. Return to A when its checks complete and confirm the reported tip still
   matches.
5. Resolve a confirmed Mechanical CI failure or hand unexpected results back to
   the appropriate owner.

Without authorized B or permitted C, finish the handoff or stop.
