from __future__ import annotations

from app.adapters.synthetic_providers import SyntheticBankingProvider


def test_synthetic_provider_returns_stable_context() -> None:
    provider = SyntheticBankingProvider()

    results = provider.collect_context("cust_1001", "acct_2001", "txn_3001")

    assert [result.record_type for result in results] == ["customer", "account", "transaction"]
    assert results[2].payload["merchant_name"] == "Synthetic Books"
    assert len(results[2].response_hash) == 64


def test_synthetic_provider_surface_is_read_only() -> None:
    public_methods = {
        name
        for name in dir(SyntheticBankingProvider)
        if not name.startswith("_") and callable(getattr(SyntheticBankingProvider, name))
    }

    assert {"get_customer", "get_account", "get_transaction", "collect_context"} <= public_methods
    forbidden = {"post_refund", "post_credit", "post_debit", "post_chargeback", "execute_payment"}
    assert public_methods.isdisjoint(forbidden)
