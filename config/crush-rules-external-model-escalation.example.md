# External model escalation (all lanes)

When you encounter any of these conditions, **tell Ryan explicitly** that an
external model (ChatGPT or Claude) would add value. Name the model, say why,
and suggest what to ask them. Do not wait for Ryan to think of it.

## When to suggest ChatGPT

ChatGPT excels at: research synthesis, finding holes in plans, identifying false
dichotomies, proposing alternative framings, and structured comparison of options.

**Suggest ChatGPT when:**
- You are planning an arc with 2+ viable options and no clear winner
- You need to identify risks or gaps in a plan before locking it
- A problem has been re-approached 2+ times without resolution
- You need a fresh perspective on "what are we missing?"
- The work involves a domain where breadth of knowledge matters more than
  codebase-specific depth (e.g. backup strategies, security posture, eval
  methodology)

## When to suggest Claude

Claude excels at: deep architecture review, adversarial critique of code
contracts, finding subtle invariant violations, and careful independent
verification of claims made by other models.

**Suggest Claude when:**
- An architecture document is about to be locked and hasn't had independent review
- A security-sensitive or irreversible design needs adversarial critique
- You need verification that implementation matches a locked contract
- Two internal models (Codex + Cursor, or Crush + Kiro) have produced
  conflicting assessments
- A complex module needs someone to "try to break it" conceptually

## Format

When you detect a trigger condition, say:

> **External model recommended:** [ChatGPT | Claude] for [one-line reason].
> Suggested prompt: "[what to ask them, 1-2 sentences]"
> This would help because: [what gap it fills that I cannot]

## When NOT to suggest external models

- Routine implementation, bug fixes, or mechanical tasks
- When the decision is already locked and doesn't need re-litigation
- When the answer is clearly in the corpus (search first)
- When the work is time-sensitive and the external round-trip would block progress
  unnecessarily

## Examples from project history

- Shadow Ledger Phase 0: ChatGPT reviewed the architecture before lock (found no
  false dichotomies but validated the direction)
- Complete-data backup: Claude recommended the hybrid consistency bar
- JudgeBench: DeepSeek Flash + ChatGPT analyzed the LLM judge problem space before
  architecture
- CG-1: Claude received a full handoff for independent architecture review (G4a)
- Global protocol: Both Claude and ChatGPT reviewed the surface-generation plan
