"""Corrective VI adversarial regressions — closure-introspection reachability closed."""
# pylint: disable=duplicate-code,protected-access

from __future__ import annotations

import secrets
import unittest
from types import CellType

import eval_corpus.r2b_v2._authority_vault as authority_vault
from eval_corpus.r2b_v2._authority_capability import (
    AuthorityCapabilityError,
    AuthorityMintCapability,
)
from eval_corpus.r2b_v2._authority_vault import (
    AuthorityRegistryError,
    MintPhase,
    _binding_digest,
)
from eval_corpus.r2b_v2.trusted import _reset_for_tests


def _closure_freevar_map(func: object) -> dict[str, object]:
    code = getattr(func, "__code__", None)
    closure = getattr(func, "__closure__", None)
    if code is None or not closure:
        return {}
    names = code.co_freevars
    out: dict[str, object] = {}
    for index, name in enumerate(names):
        cell = closure[index]
        if isinstance(cell, CellType):
            out[name] = cell.cell_contents
    return out


class R2bV2CorrectiveVIAdversarialTests(unittest.TestCase):
    def setUp(self) -> None:
        _reset_for_tests()

    def test_01_module_dispatch_has_no_reachable_vault_closure(self) -> None:
        self.assertIsNone(authority_vault.vault_dispatch.__closure__)
        forbidden = {
            "_capability_ledger",
            "_consumed_capability_ids",
            "_issue_capability",
            "registry",
        }
        cells = _closure_freevar_map(authority_vault.vault_dispatch)
        self.assertFalse(forbidden.intersection(cells))

    def test_02_closure_ledger_injection_cannot_validate_forged_capability(self) -> None:
        holder = object.__getattribute__(authority_vault, "_vault_holder")
        inner = object.__getattribute__(holder, "_VaultHolder__inner")
        cells = _closure_freevar_map(inner)
        ledger = cells.get("_capability_ledger")
        self.assertIsNotNone(ledger)
        binding = {
            "coverage_digest": "fake",
            "gate_identity": "fake",
            "code_revision": "a" * 40,
        }
        phase = MintPhase.CENSUS
        cap_id = secrets.token_hex(16)
        with self.assertRaises(AuthorityCapabilityError):
            ledger[cap_id] = {
                "phase": phase,
                "binding_digest": _binding_digest(phase, binding),
                "trust_class": "production",
                "census_stage": 0,
            }
        forged = object.__new__(AuthorityMintCapability)
        object.__setattr__(forged, "_capability_id", cap_id)
        with self.assertRaises(AuthorityCapabilityError):
            forged._validate_binding(phase=phase, binding=binding)

    def test_03_closure_mutation_token_replay_cannot_mutate_sealed_store(self) -> None:
        holder = object.__getattribute__(authority_vault, "_vault_holder")
        inner = object.__getattribute__(holder, "_VaultHolder__inner")
        cells = _closure_freevar_map(inner)
        registry = cells.get("registry")
        self.assertIsNotNone(registry)
        store = registry._lease_records
        guard = store._guard_mutation
        self.assertIsNone(guard.__closure__)
        with self.assertRaises(AuthorityRegistryError):
            store["evil_injected"] = "payload"

    def test_04_direct_consumed_capability_set_mutation_forbidden(self) -> None:
        holder = object.__getattribute__(authority_vault, "_vault_holder")
        inner = object.__getattribute__(holder, "_VaultHolder__inner")
        cells = _closure_freevar_map(inner)
        consumed = cells.get("_consumed_capability_ids")
        self.assertIsNotNone(consumed)
        with self.assertRaises(AuthorityCapabilityError):
            consumed.add("forged-capability-id")

    def test_05_mutation_guard_does_not_close_over_contextvar_or_sentinel(self) -> None:
        holder = object.__getattribute__(authority_vault, "_vault_holder")
        inner = object.__getattribute__(holder, "_VaultHolder__inner")
        cells = _closure_freevar_map(inner)
        registry = cells["registry"]
        guard = registry._lease_records._guard_mutation
        self.assertEqual(guard.__code__.co_freevars, ())
        self.assertIsNone(guard.__closure__)


if __name__ == "__main__":
    unittest.main()
