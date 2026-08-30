import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";

import App from "./App";

const caseResponse = {
  case_id: "9c0ce16d-2f8d-4dd2-8b46-3380c822ec8b",
  customer_ref: "cust_1001",
  account_ref: "acct_2001",
  transaction_ref: "txn_3001",
  channel: "web",
  dispute_type: "duplicate_card_transaction",
  description: "Customer reports a duplicate card transaction at Synthetic Books.",
  status: "Submitted",
  correlation_id: "corr-demo-001",
  state_version: 1,
  opened_at: "2026-08-29T00:00:00Z",
  closed_at: null,
  channel_metadata: {},
  submitted_at: "2026-08-29T00:00:00Z",
  created_at: "2026-08-29T00:00:00Z",
  updated_at: "2026-08-29T00:00:00Z",
  timeline: [
    {
      timeline_entry_id: "4f4e6d22-5f3d-4705-936c-a8af73d7a7a0",
      event_type: "CASE_CREATED",
      message: "Synthetic dispute case created.",
      audit_event_id: "4b7dc03a-d9cc-4d66-8b9f-28d8cb7c9620",
      correlation_id: "corr-demo-001",
      occurred_at: "2026-08-29T00:00:00Z"
    }
  ],
  evidence_metadata: [
    {
      evidence_id: "57d32387-3872-4a4a-a8de-fce175d1007a",
      file_name: "receipt.png",
      content_type: "image/png",
      size_bytes: 1204,
      checksum_sha256: "a".repeat(64),
      uploader_ref: "customer:cust_1001",
      registered_at: "2026-08-29T00:00:00Z"
    }
  ],
  provider_context: [
    {
      provider_context_id: "ef09cdf6-618d-471d-b409-4ff06de22a58",
      provider_name: "SyntheticTransactionProvider",
      source_record_ref: "txn_3001",
      record_type: "transaction",
      payload_json: {},
      response_hash: "b".repeat(64),
      response_version: "synthetic-foundation-v1",
      correlation_id: "corr-demo-001",
      retrieved_at: "2026-08-29T00:00:00Z"
    }
  ],
  audit_events: [
    {
      audit_event_id: "4b7dc03a-d9cc-4d66-8b9f-28d8cb7c9620",
      event_type: "CASE_CREATED",
      actor_type: "SERVICE",
      actor_ref: "case-service",
      source: "foundation-api",
      object_ref: "9c0ce16d-2f8d-4dd2-8b46-3380c822ec8b",
      correlation_id: "corr-demo-001",
      created_at: "2026-08-29T00:00:00Z"
    }
  ]
};

beforeEach(() => {
  vi.restoreAllMocks();
});

test("validates required fields before submit", async () => {
  const user = userEvent.setup();
  render(<App />);

  await user.clear(screen.getByLabelText(/transaction reference/i));
  await user.click(screen.getByRole("button", { name: /create synthetic case/i }));

  expect(screen.getByRole("alert")).toHaveTextContent("Transaction reference is required.");
});

test("creates and renders foundation case details", async () => {
  const user = userEvent.setup();
  vi.spyOn(globalThis, "fetch").mockResolvedValue({
    ok: true,
    json: async () => caseResponse
  } as Response);

  render(<App />);
  await user.click(screen.getByRole("button", { name: /create synthetic case/i }));

  expect(await screen.findByText(/Created case/)).toBeInTheDocument();
  expect(screen.getByText("Submitted")).toBeInTheDocument();
  expect(screen.getByText("corr-demo-001")).toBeInTheDocument();
  expect(screen.getAllByText("CASE_CREATED")).toHaveLength(2);
  expect(screen.getByText("receipt.png")).toBeInTheDocument();
  expect(screen.getByText(/SyntheticTransactionProvider/)).toBeInTheDocument();
});

test("shows a visible error when case creation fails", async () => {
  const user = userEvent.setup();
  vi.spyOn(globalThis, "fetch").mockResolvedValue({
    ok: false,
    status: 503,
    json: async () => ({ detail: "Backend unavailable" })
  } as Response);

  render(<App />);
  await user.click(screen.getByRole("button", { name: /create synthetic case/i }));

  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Create dispute failed (503): Backend unavailable"
  );
  expect(screen.getByRole("button", { name: /create synthetic case/i })).toBeEnabled();
});

test("shows a visible error when case lookup fails", async () => {
  const user = userEvent.setup();
  vi.spyOn(globalThis, "fetch").mockResolvedValue({
    ok: false,
    status: 404,
    json: async () => ({ detail: "Case not found" })
  } as Response);

  render(<App />);
  await user.type(screen.getByLabelText(/case id/i), "missing-case");
  await user.click(screen.getByRole("button", { name: /load case/i }));

  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Load dispute failed (404): Case not found"
  );
  expect(screen.getByRole("button", { name: /load case/i })).toBeEnabled();
});
