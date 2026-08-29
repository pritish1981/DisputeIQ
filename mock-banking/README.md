# Synthetic Banking Providers

`001-platform-foundation` uses read-only synthetic customer, account, and transaction provider fixtures to attach authoritative mock facts to a case.

Foundation provider rules:

- Providers expose read-only retrieval behavior only.
- Provider context includes source lineage and response hash/version metadata.
- No provider can post refunds, credits, debits, chargebacks, or other material financial outcomes.

Settlement, merchant, and refund provider read models are introduced in later workflow/context changes when their scenarios need them.
