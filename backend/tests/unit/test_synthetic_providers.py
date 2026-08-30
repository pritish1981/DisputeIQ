from __future__ import annotations

from app.adapters.synthetic_providers import (
    AccountProvider,
    CustomerProvider,
    MerchantProvider,
    RefundProvider,
    SettlementProvider,
    SyntheticBankingProvider,
    TransactionProvider,
)


def test_synthetic_provider_returns_six_stable_context_records() -> None:
    provider = SyntheticBankingProvider()
    results = provider.collect_context("cust_1001", "acct_2001", "txn_3001")

    assert [result.record_type for result in results] == [
        "customer",
        "account",
        "transaction",
        "merchant",
        "settlement",
        "refund",
    ]
    assert results[3].facts["merchant_name"] == "Synthetic Books"
    assert all(len(result.response_hash) == 64 for result in results)
    assert all(result.source_version == "synthetic-phase-002-v1" for result in results)


def test_provider_contracts_are_structurally_read_only() -> None:
    protocols = [
        TransactionProvider,
        CustomerProvider,
        AccountProvider,
        MerchantProvider,
        SettlementProvider,
        RefundProvider,
    ]
    forbidden = {
        "post_refund",
        "post_credit",
        "post_debit",
        "post_chargeback",
        "post_settlement",
        "execute_payment",
    }
    for contract in protocols:
        public_methods = {
            name
            for name in contract.__dict__
            if not name.startswith("_") and callable(getattr(contract, name))
        }
        assert public_methods
        assert public_methods.isdisjoint(forbidden)

    runtime_methods = {
        name
        for name in dir(SyntheticBankingProvider)
        if not name.startswith("_") and callable(getattr(SyntheticBankingProvider, name))
    }
    assert runtime_methods.isdisjoint(forbidden)
