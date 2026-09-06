from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol


@dataclass(frozen=True)
class ProviderRecord:
    provider_name: str
    record_type: str
    source_record_ref: str
    facts: dict[str, object]
    response_hash: str
    source_version: str
    retrieved_at: datetime

    @property
    def payload(self) -> dict[str, object]:
        return self.facts

    @property
    def response_version(self) -> str:
        return self.source_version


ProviderResult = ProviderRecord


class CustomerProvider(Protocol):
    def get_customer(self, customer_ref: str) -> ProviderRecord: ...


class AccountProvider(Protocol):
    def get_account(self, account_ref: str | None, customer_ref: str) -> ProviderRecord: ...


class TransactionProvider(Protocol):
    def get_transaction(self, transaction_ref: str) -> ProviderRecord: ...


class MerchantProvider(Protocol):
    def get_merchant(self, merchant_ref: str) -> ProviderRecord: ...


class SettlementProvider(Protocol):
    def get_settlement(self, settlement_ref: str) -> ProviderRecord: ...


class RefundProvider(Protocol):
    def get_refund(self, refund_ref: str) -> ProviderRecord: ...


ReadOnlyCustomerProvider = CustomerProvider
ReadOnlyAccountProvider = AccountProvider
ReadOnlyTransactionProvider = TransactionProvider


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
        "merchant_ref": "mrc_4001",
        "settlement_ref": "stl_5001",
        "refund_ref": "rfd_6001",
        "amount": "49.99",
        "currency": "USD",
        "authorized_at": "2026-08-28T10:15:00Z",
        "network_status": "settled",
        "possible_duplicate_ref": "txn_3002",
    }
}

MERCHANTS: dict[str, dict[str, object]] = {
    "mrc_4001": {
        "merchant_ref": "mrc_4001",
        "merchant_name": "Synthetic Books",
        "category_code": "5942",
        "country": "US",
    }
}

SETTLEMENTS: dict[str, dict[str, object]] = {
    "stl_5001": {
        "settlement_ref": "stl_5001",
        "transaction_ref": "txn_3001",
        "status": "settled",
        "settled_at": "2026-08-29T02:00:00Z",
    }
}

REFUNDS: dict[str, dict[str, object]] = {
    "rfd_6001": {
        "refund_ref": "rfd_6001",
        "transaction_ref": "txn_3001",
        "status": "not_refunded",
        "amount": "0.00",
        "currency": "USD",
    }
}


class SyntheticProviderError(LookupError):
    pass


class SyntheticBankingProvider:
    source_version = "synthetic-phase-002-v1"

    def get_customer(self, customer_ref: str) -> ProviderRecord:
        return self._lookup("SyntheticCustomerProvider", "customer", customer_ref, CUSTOMERS)

    def get_account(self, account_ref: str | None, customer_ref: str) -> ProviderRecord:
        if account_ref is not None and account_ref in ACCOUNTS:
            return self._result(
                "SyntheticAccountProvider", "account", account_ref, ACCOUNTS[account_ref]
            )
        for candidate_ref, account in ACCOUNTS.items():
            if account["customer_ref"] == customer_ref:
                return self._result("SyntheticAccountProvider", "account", candidate_ref, account)
        raise SyntheticProviderError(f"Unknown synthetic account for customer: {customer_ref}")

    def get_transaction(self, transaction_ref: str) -> ProviderRecord:
        return self._lookup(
            "SyntheticTransactionProvider", "transaction", transaction_ref, TRANSACTIONS
        )

    def get_merchant(self, merchant_ref: str) -> ProviderRecord:
        return self._lookup("SyntheticMerchantProvider", "merchant", merchant_ref, MERCHANTS)

    def get_settlement(self, settlement_ref: str) -> ProviderRecord:
        return self._lookup(
            "SyntheticSettlementProvider", "settlement", settlement_ref, SETTLEMENTS
        )

    def get_refund(self, refund_ref: str) -> ProviderRecord:
        return self._lookup("SyntheticRefundProvider", "refund", refund_ref, REFUNDS)

    def collect_context(
        self, customer_ref: str, account_ref: str | None, transaction_ref: str
    ) -> list[ProviderRecord]:
        customer = self.get_customer(customer_ref)
        account = self.get_account(account_ref, customer_ref)
        transaction = self.get_transaction(transaction_ref)
        merchant = self.get_merchant(str(transaction.facts["merchant_ref"]))
        settlement = self.get_settlement(str(transaction.facts["settlement_ref"]))
        refund = self.get_refund(str(transaction.facts["refund_ref"]))
        return [customer, account, transaction, merchant, settlement, refund]

    def _lookup(
        self,
        provider_name: str,
        record_type: str,
        source_ref: str,
        records: dict[str, dict[str, object]],
    ) -> ProviderRecord:
        try:
            payload = records[source_ref]
        except KeyError as exc:
            raise SyntheticProviderError(f"Unknown synthetic {record_type}: {source_ref}") from exc
        return self._result(provider_name, record_type, source_ref, payload)

    def _result(
        self,
        provider_name: str,
        record_type: str,
        source_record_ref: str,
        payload: dict[str, object],
    ) -> ProviderRecord:
        payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return ProviderRecord(
            provider_name=provider_name,
            record_type=record_type,
            source_record_ref=source_record_ref,
            facts=dict(payload),
            response_hash=hashlib.sha256(payload_json.encode("utf-8")).hexdigest(),
            source_version=self.source_version,
            retrieved_at=datetime.now(UTC),
        )
