from __future__ import annotations

from collections.abc import Callable
from functools import partial
from typing import Any

from app.adapters.synthetic_providers import ProviderRecord, SyntheticBankingProvider
from app.domain.controls import EvidenceItem, digest


class ControlContextAdapter:
    def __init__(self, provider: SyntheticBankingProvider | None = None) -> None:
        self.provider = provider or SyntheticBankingProvider()

    def acquire(self, case: dict[str, Any]) -> tuple[dict[str, Any], list[EvidenceItem]]:
        facts: dict[str, Any] = {
            "customer_ref": case["customer_ref"],
            "dispute_type": case["dispute_type"],
            "submitted_at": case["submitted_at"],
            "references": [],
            "provider_records": [],
            "provider_errors": [],
            "required_operations": 8,
        }
        items = []

        def capture(
            name: str,
            operation: Callable[[], ProviderRecord],
            expected_ref: Callable[[], object],
        ) -> None:
            try:
                record = operation()
                expected = expected_ref()
                if expected is not None and record.source_record_ref != expected:
                    raise ValueError("Provider returned a different requested record")
                if record.facts.get(f"{record.record_type}_ref") != record.source_record_ref:
                    raise ValueError("Invalid provider lineage")
                if (
                    digest(record.facts) != record.response_hash
                ):  # validate serializable finite facts before admission
                    raise ValueError("Invalid provider data")
                reference = (
                    f"{record.provider_name}:{record.source_record_ref}:{record.source_version}"
                )
                facts[name] = dict(record.facts)
                facts["references"].append(reference)
                facts["provider_records"].append(
                    {
                        "reference": reference,
                        "name": name,
                        "source_version": record.source_version,
                        "response_hash": record.response_hash,
                        "source_as_of": record.source_as_of.isoformat()
                        if record.source_as_of
                        else None,
                        "retrieved_at": record.retrieved_at.isoformat(),
                        "facts": record.facts,
                    }
                )
                items.append(
                    EvidenceItem(
                        reference=reference,
                        kind=name,
                        checksum=record.response_hash,
                        state="validated",
                        source_as_of=record.source_as_of,
                        subject=f"{record.record_type}:{record.source_record_ref}",
                        attributes={key: str(value) for key, value in record.facts.items()},
                    )
                )
            except (LookupError, TimeoutError, ConnectionError, ValueError, KeyError):
                facts[name] = {}
                facts["provider_errors"].append(f"PROVIDER_UNAVAILABLE:{name}")
                items.append(
                    EvidenceItem(
                        reference=f"unavailable:{name}", kind=name, checksum="", state="unavailable"
                    )
                )

        capture(
            "account",
            lambda: self.provider.get_account(case.get("account_ref"), case["customer_ref"]),
            lambda: case.get("account_ref"),
        )
        capture(
            "disputed",
            lambda: self.provider.get_transaction(case["transaction_ref"]),
            lambda: case["transaction_ref"],
        )
        capture(
            "candidate",
            lambda: self.provider.get_transaction(facts["disputed"]["possible_duplicate_ref"]),
            lambda: facts["disputed"]["possible_duplicate_ref"],
        )
        capture(
            "merchant",
            lambda: self.provider.get_merchant(facts["disputed"]["merchant_ref"]),
            lambda: facts["disputed"]["merchant_ref"],
        )
        for name in ("disputed", "candidate"):
            capture(
                f"{name}_settlement",
                partial(self._settlement, facts, name),
                partial(self._reference, facts, name, "settlement_ref"),
            )
            capture(
                f"{name}_refund",
                partial(self._refund, facts, name),
                partial(self._reference, facts, name, "refund_ref"),
            )
        return facts, items

    def _reference(self, facts: dict[str, Any], name: str, key: str) -> object:
        return facts[name][key]

    def _settlement(self, facts: dict[str, Any], name: str) -> ProviderRecord:
        return self.provider.get_settlement(facts[name]["settlement_ref"])

    def _refund(self, facts: dict[str, Any], name: str) -> ProviderRecord:
        return self.provider.get_refund(facts[name]["refund_ref"])
