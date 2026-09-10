import { FormEvent, useState } from "react";
import { ControlViewer } from "./ControlViewer";

import { CreateDisputeInput, DisputeCase, createDispute, getDispute } from "./api";
import "./styles.css";

const defaultForm: CreateDisputeInput = {
  customer_ref: "cust_1001",
  account_ref: "acct_2001",
  transaction_ref: "txn_3001",
  channel: "web",
  description: "Customer reports a duplicate card transaction at Synthetic Books.",
  dispute_type: "duplicate_card_transaction",
  evidence_metadata: [
    {
      file_name: "receipt.png",
      content_type: "image/png",
      size_bytes: 1204,
      checksum_sha256: "a".repeat(64),
      uploader_ref: "customer:cust_1001"
    }
  ]
};

function validateForm(form: CreateDisputeInput): string[] {
  const errors: string[] = [];
  if (!form.customer_ref.trim()) errors.push("Customer reference is required.");
  if (!form.transaction_ref.trim()) errors.push("Transaction reference is required.");
  if (form.description.trim().length < 10) errors.push("Description must be at least 10 characters.");
  return errors;
}

function requestError(error: unknown): string {
  return error instanceof Error ? error.message : "The request failed unexpectedly.";
}

export default function App() {
  const [form, setForm] = useState<CreateDisputeInput>(defaultForm);
  const [idempotencyKey, setIdempotencyKey] = useState("demo-idem-001");
  const [correlationId, setCorrelationId] = useState("corr-demo-001");
  const [caseIdLookup, setCaseIdLookup] = useState("");
  const [currentCase, setCurrentCase] = useState<DisputeCase | null>(null);
  const [errors, setErrors] = useState<string[]>([]);
  const [message, setMessage] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const validationErrors = validateForm(form);
    if (validationErrors.length > 0) {
      setErrors(validationErrors);
      setMessage("");
      return;
    }

    setErrors([]);
    setMessage("");
    setIsCreating(true);
    try {
      const created = await createDispute(form, idempotencyKey, correlationId || undefined);
      setCurrentCase(created);
      setCaseIdLookup(created.case_id);
      setMessage(`Created case ${created.case_id}`);
    } catch (error) {
      setErrors([requestError(error)]);
    } finally {
      setIsCreating(false);
    }
  }

  async function onLookup() {
    if (!caseIdLookup.trim()) {
      setErrors(["Case ID is required for lookup."]);
      return;
    }
    setErrors([]);
    setMessage("");
    setIsLoading(true);
    try {
      const detail = await getDispute(caseIdLookup.trim());
      setCurrentCase(detail);
      setMessage(`Loaded case ${detail.case_id}`);
    } catch (error) {
      setErrors([requestError(error)]);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main className="shell">
      <section className="panel">
        <h1>DisputeIQ Foundation</h1>
        <form onSubmit={onSubmit} aria-label="Create dispute case">
          <label>
            Customer reference
            <input
              value={form.customer_ref}
              onChange={(event) => setForm({ ...form, customer_ref: event.target.value })}
            />
          </label>
          <label>
            Account reference
            <input
              value={form.account_ref}
              onChange={(event) => setForm({ ...form, account_ref: event.target.value })}
            />
          </label>
          <label>
            Transaction reference
            <input
              value={form.transaction_ref}
              onChange={(event) => setForm({ ...form, transaction_ref: event.target.value })}
            />
          </label>
          <label>
            Channel
            <select
              value={form.channel}
              onChange={(event) => setForm({ ...form, channel: event.target.value })}
            >
              <option value="web">Web</option>
              <option value="mobile">Mobile</option>
              <option value="analyst">Analyst</option>
              <option value="partner_api">Partner API</option>
            </select>
          </label>
          <label>
            Description
            <textarea
              value={form.description}
              onChange={(event) => setForm({ ...form, description: event.target.value })}
            />
          </label>
          <label>
            Idempotency key
            <input value={idempotencyKey} onChange={(event) => setIdempotencyKey(event.target.value)} />
          </label>
          <label>
            Correlation ID
            <input value={correlationId} onChange={(event) => setCorrelationId(event.target.value)} />
          </label>
          <button type="submit" disabled={isCreating}>
            {isCreating ? "Creating case..." : "Create synthetic case"}
          </button>
        </form>
      </section>

      <section className="panel">
        <h2>Case Lookup</h2>
        <div className="lookup">
          <input
            aria-label="Case ID"
            value={caseIdLookup}
            onChange={(event) => setCaseIdLookup(event.target.value)}
          />
          <button type="button" onClick={onLookup} disabled={isLoading}>
            {isLoading ? "Loading case..." : "Load case"}
          </button>
        </div>

        {errors.length > 0 && (
          <ul role="alert" className="errors">
            {errors.map((error) => (
              <li key={error}>{error}</li>
            ))}
          </ul>
        )}
        {message && <p className="message">{message}</p>}

        {currentCase && <CaseDetail disputeCase={currentCase} />}
      </section>
      <ControlViewer />
    </main>
  );
}

function CaseDetail({ disputeCase }: { disputeCase: DisputeCase }) {
  return (
    <article className="detail">
      <h2>Case {disputeCase.case_id}</h2>
      <dl>
        <dt>Status</dt>
        <dd>{disputeCase.status}</dd>
        <dt>Correlation ID</dt>
        <dd>{disputeCase.correlation_id}</dd>
        <dt>Transaction</dt>
        <dd>{disputeCase.transaction_ref}</dd>
      </dl>

      <h3>Timeline</h3>
      <ul>
        {disputeCase.timeline.map((entry) => (
          <li key={entry.timeline_entry_id}>{entry.event_type}</li>
        ))}
      </ul>

      <h3>Evidence Metadata</h3>
      <ul>
        {disputeCase.evidence_metadata.map((evidence) => (
          <li key={evidence.evidence_id ?? evidence.file_name}>{evidence.file_name}</li>
        ))}
      </ul>

      <h3>Provider Context</h3>
      <ul>
        {disputeCase.provider_context.map((context) => (
          <li key={context.provider_context_id}>
            {context.provider_name}: {context.source_record_ref}
          </li>
        ))}
      </ul>

      <h3>Audit Events</h3>
      <ul>
        {disputeCase.audit_events.map((event) => (
          <li key={event.audit_event_id}>{event.event_type}</li>
        ))}
      </ul>
    </article>
  );
}
