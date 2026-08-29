from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol


class ReadOnlyCustomerProvider(Protocol):
    def get_customer(self, customer_ref: str) -> dict[str, object]: ...


class ReadOnlyAccountProvider(Protocol):
    def get_account(self, account_ref: str | None, customer_ref: str) -> dict[str, object]: ...


class ReadOnlyTransactionProvider(Protocol):
    def get_transaction(self, transaction_ref: str) -> dict[str, object]: ...


CUSTOMERS: dict[str, dict[str, object]] = {
    "cust_1001": {
        "customer_ref": "cust_1001",
        "display_name": "Synthetic Customer 1001",
        "segment": "retail",
    }
}

ACCOUNTS: dict[str, dict[str, object]] = {
    "acct_2001": {
        "account_ref": "acct_2001",
        "customer_ref": "cust_1001",
        "product": "card",
        "status": "active",
    }
}

TRANSACTIONS: dict[str, dict[str, object]] = {
    "txn_3001": {
        "transaction_ref": "txn_3001",
        "account_ref": "acct_2001",
        "merchant_name": "Synthetic Books",
        "amount": "49.99",
        "currency": "USD",
        "authorized_at": "2026-08-28T10:15:00Z",
        "network_status": "settled",
        "possible_duplicate_ref": "txn_3002",
    }
}


@dataclass(frozen=True)
class ProviderResult:
    provider_name: str
    record_type: str
    source_record_ref: str
    payload: dict[str, object]
    response_hash: str
    response_version: str
    retrieved_at: datetime


class SyntheticProviderError(LookupError):
    pass


class SyntheticBankingProvider:
    response_version = "synthetic-foundation-v1"

    def get_customer(self, customer_ref: str) -> dict[str, object]:
        try:
            return CUSTOMERS[customer_ref]
        except KeyError as exc:
            raise SyntheticProviderError(f"Unknown synthetic customer: {customer_ref}") from exc

    def get_account(self, account_ref: str | None, customer_ref: str) -> dict[str, object]:
        if account_ref is not None and account_ref in ACCOUNTS:
            return ACCOUNTS[account_ref]
        for account in ACCOUNTS.values():
            if account["customer_ref"] == customer_ref:
                return account
        raise SyntheticProviderError(f"Unknown synthetic account for customer: {customer_ref}")

    def get_transaction(self, transaction_ref: str) -> dict[str, object]:
        try:
            return TRANSACTIONS[transaction_ref]
        except KeyError as exc:
            message = f"Unknown synthetic transaction: {transaction_ref}"
            raise SyntheticProviderError(message) from exc

    def collect_context(
        self, customer_ref: str, account_ref: str | None, transaction_ref: str
    ) -> list[ProviderResult]:
        customer = self.get_customer(customer_ref)
        account = self.get_account(account_ref, customer_ref)
        transaction = self.get_transaction(transaction_ref)
        return [
            self._result("SyntheticCustomerProvider", "customer", customer_ref, customer),
            self._result(
                "SyntheticAccountProvider", "account", str(account["account_ref"]), account
            ),
            self._result(
                "SyntheticTransactionProvider",
                "transaction",
                transaction_ref,
                transaction,
            ),
        ]

    def _result(
        self,
        provider_name: str,
        record_type: str,
        source_record_ref: str,
        payload: dict[str, object],
    ) -> ProviderResult:
        payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return ProviderResult(
            provider_name=provider_name,
            record_type=record_type,
            source_record_ref=source_record_ref,
            payload=payload,
            response_hash=hashlib.sha256(payload_json.encode("utf-8")).hexdigest(),
            response_version=self.response_version,
            retrieved_at=datetime.now(UTC),
        )
