# CURSOR — Ack ChatGPT routing fixes (stale verification metadata)

**Date:** 2026-07-16
**From:** Cursor
**Subject:** ChatGPT remaining documentation red flags on the verification package

| Item | Action |
|---|---|
| Stale file still said “Shipped… awaiting verification” under STALE banner | Status line → **SUPERSEDED — first-round record only** |
| README verification row not labeled STALE | Row now: **STALE** first-round checklist — do not use |
| Fix plan | Remains **APPROVED for execution**; awaiting Ryan **go** for §§1–4 |
| R1 / V4 “ready for merge” on `503add7` | Still **superseded** — checklist would not catch numbering / empty shape / Pylint |

No code tip change. Remote PR tip remains `503add7`.
