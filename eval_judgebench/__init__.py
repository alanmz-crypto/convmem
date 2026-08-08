"""JudgeBench offline semantic calibration package (structure and prep).

Tier 1 (DeepSeek V4 Flash, Crush lane) owns slices S1-S9 only - contracts,
structural validators, rubric loader, registry loader, and import guards.
OFF-LIMITS surfaces live elsewhere: identity classification, provenance
comparison-signature, runner orchestration, legacy shim, gold/case authoring.

See docs/plans/EXECUTION-judgebench-flash-slices.md for the slice brief and
escalation wall.
"""

from __future__ import annotations
