# Kiro Verification Handoff — DeepSeek max-tokens reservation causing context-window overflow

**Date:** 2026-08-20
**From:** Crush (discovery/analysis lane)
**To:** Kiro (design / sign-off lane)
**Branch:** `docs/2026-08-20-crush-deepseek-max-tokens-verification`
**Repo:** `/home/lauer/Projects/convmem`
**Type:** Read-only verification request — no code, no runtime change.

---

## TL;DR for Kiro

Crush diagnosed why a normal DeepSeek V4 operational step in Crush hit "over context window."
The **384000** completion-token figure is **DeepSeek V4's real max-output cap** (official), not a
stray provider reservation. But it **is** the mechanism that causes overflow, because Crush config
sets `"default_max_tokens": -1` (no cap) on every model, and DeepSeek charges
`input_tokens + max_tokens` against the 1M window. On a mid-size operational transcript (~600K
input), the 384K reserved output slot tips `input + max_tokens` past 1,000,000 → "over context
window." **Fixable** by capping `default_max_tokens` to a sane operating bound (8–16K) on the
DeepSeek models.

**Crush has NOT changed any file at this branch tip.** This is a proposal + evidence package for
your independent verification. Nothing is applied to `~/.config/crush/crush.json`.

---

## Task for Kiro

Independently verify the **diagnosis** (is the mechanism correct?) and the **fix proposal**
(is capping `default_max_tokens` the right minimal correction, and what value/scope?).

### Scope (do / do not)

| Do | Do not |
|----|--------|
| Verify the DeepSeek V4 output-cap / context facts | Implement any code or config change |
| Verify the `input_tokens + max_tokens` overflow mechanism | Edit files on this branch |
| Verify that `-1` means "no cap" and thus reserves DeepSeek's max in Crush | Expand scope beyond this handoff |
| Assess the proposed fix value/scope (8K vs 16K, both models vs all) | Run the Crush binary / live corpus |
| Record PASS / CONDITIONAL PASS / FAIL with findings | |

### Required output

1. Verdict: **PASS**, **CONDITIONAL PASS**, or **FAIL**
2. Blocking findings (if any) — each with the claim it refutes
3. Nonblocking findings / recommendations
4. A recommended `default_max_tokens` value and model scope, or a reasoned objection

---

## Evidence / claims to verify

### Claim 1 — 384K is DeepSeek V4's genuine max output, not a stray reservation

- Source: DeepSeek official API pricing doc (`https://api-docs.deepseek.com/quick_start/pricing`).
  Both `deepseek-v4-flash` and `deepseek-v4-pro`: **Context length 1M** (1,000,000), **Max output
  384K** (384,000). Thinking and non-thinking modes both supported.
- This means the `384000` figure is **expected** when no client-side cap is set — not a
  misconfiguration reservation.

### Claim 2 — Crush config sets `-1` (no cap) on every model

From `/home/lauer/.config/crush/crush.json` (the live Crush config), every model object across
all providers carries `"default_max_tokens": -1`. Relevant excerpts:

- **deepseek** provider: `deepseek-v4-flash` and `deepseek-v4-pro` both have
  `"context_window": 1000000` and `"default_max_tokens": -1`.
- All `ollama-*`, `alibaba`, `deepinfra`, `gemini`, `tokenrouter` models also use `-1`.

`-1` in this schema means "no client-side cap," so the provider's own maximum output budget is used.

### Claim 3 — the overflow mechanism is `input + max_tokens` charging

On an operational transcript where the session context has already accumulated a large number of
input tokens (repeated ritual/hook output, prior tool dumps), the request's required window is
approximately:

```
required_window ≈ input_tokens + max_tokens
```

With `max_tokens` free to be DeepSeek's full 384K:

```
~600K input + 384K reserved output ≈ 984K+  →  exceeds 1,000,000  →  "over context window"
```

Even a step that needs only a short answer is charged the full 384K output slot, so the far-from-full
input window still overflows.

### Claim 4 — this manifests even in title generation

Crush logs (`crush_logs`) show repeated `Title generation hit token limit with small model; trying
next` and `...large model...` errors at short update times (e.g. 19:51–19:52). Title generation
writes a few hundred tokens at most, so hitting a "token limit" for it is a strong signal that the
binding constraint is **input accumulation + output reservation**, not real output length.

### Claim 5 — the proposed fix is a client-side `default_max_tokens` cap

Set a concrete positive `default_max_tokens` on the DeepSeek models so the reserved output slot
shrinks back into the window. For operational/tool steps 8–16K output is generous; 32K covers heavy
code generation. This both avoids the overflow and reduces billed output. (Crush has relevant
`max_tokens` behavior — the exact cap value and per-model scope are the decision for you to
recommend.)

---

## Files to read (in order)

1. `/home/lauer/.config/crush/crush.json` — the live config; confirm `"default_max_tokens": -1`
   across providers, and the `deepseek` provider's `context_window: 1000000`.
2. DeepSeek official pricing page (`https://api-docs.deepseek.com/quick_start/pricing`) — confirm
   the 1M context / 384K max-output facts for both V4 models.
3. Crush logs (`crush_logs`, recent entries) — the repeated "hit token limit" on title generation
   as supporting evidence.
4. `docs/inter-model/LATEST.md` — the Active handoff bullet for this verification request.

---

## Proposed config change (for your review only — NOT applied)

```jsonc
// /home/lauer/.config/crush/crush.json  →  deepseek provider  →  each model
{
  "id": "deepseek-v4-flash",
  "name": "DeepSeek V4 Flash",
  "context_window": 1000000,
  "default_max_tokens": 16384,   // was -1
  ...
}
```

Apply to both `deepseek-v4-flash` and `deepseek-v4-pro`. Whether to also cap the other providers'
`-1` models (ollama, qwen, gemini, etc.) is your call — the overflow risk is highest on the 1M-window
cloud models.

## Safety confirmation

This package is **read-only**: no Crush config file, runtime state, live corpus, or operational
surface is modified at this branch tip. The change above is a proposal pending your verdict and
Ryan's authorization.
