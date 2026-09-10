import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { ControlDetail, ControlViewer } from "./ControlViewer";
import type { ControlEvaluation } from "./controls";

const item: ControlEvaluation = {
  evaluation_id: "evaluation-1",
  bundle: { profile_version: "controls-v1", evaluated_at: "2026-09-10T12:00:00Z",
    versions: { evidence_contract: "evidence-v1", ruleset: "rules-v1", confidence: "confidence-v1" },
    prior_evaluation_id: "evaluation-0", inputs_hash: "hash", classification_hash: "class-hash" },
  stages: {
    evidence: { required: ["statement", "candidate"], available: ["statement-ref"], missing: ["candidate"],
      stale: [], invalid: [], conflicting: [], satisfaction: { statement: ["statement-ref"], candidate: [] },
      score: "0.500000", mandatory_complete: false, reasons: ["MISSING_EVIDENCE:candidate"] },
    rules: { candidate: "REVIEW_REQUIRED", blocked: true, results: [
      { rule_id: "evidence-rule", version: "v1", outcome: "INDETERMINATE", reason_code: "MISSING_FACTS" }
    ] },
    confidence: { score: "0.700000", threshold: "0.700000", ready: false,
      reasons: ["MANDATORY_EVIDENCE_INCOMPLETE"], factors: {
        classification: { raw: "0.9", normalized: "0.9", weight: "0.15", contribution: "0.135",
          source_ref: "class-ref", valid: true }
      } }
  },
  requests: [{ request_id: "request-1", kind: "REQUEST_ADDITIONAL_EVIDENCE", status: "OPEN",
    reasons: ["MISSING_EVIDENCE:candidate"] }]
};

afterEach(() => vi.unstubAllGlobals());

test("shows deterministic findings, evidence gaps, pins and confidence without approval controls", () => {
  render(<ControlDetail item={item} />);
  expect(screen.getByText("candidate: unsatisfied")).toBeInTheDocument();
  expect(screen.getByText("INDETERMINATE")).toBeInTheDocument();
  expect(screen.getByText("0.135")).toBeInTheDocument();
  expect(screen.getByText("rules-v1")).toBeInTheDocument();
  expect(screen.getByText(/AI classification is one input/)).toBeInTheDocument();
  expect(screen.getByText(/Mandatory gate: blocked/)).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /approve|post|refund/i })).not.toBeInTheDocument();
});

test("loads a scoped history and displays access errors without stale results", async () => {
  const fetcher = vi.fn().mockResolvedValueOnce({ ok: true, json: async () => ({ items: [item] }) })
    .mockResolvedValueOnce({ ok: false, status: 403 });
  vi.stubGlobal("fetch", fetcher);
  render(<ControlViewer />);
  fireEvent.change(screen.getByLabelText("Workflow ID"), { target: { value: "workflow-1" } });
  fireEvent.click(screen.getByRole("button", { name: "Load evaluations" }));
  expect(await screen.findByText("Evaluation evaluation-1")).toBeInTheDocument();
  expect(fetcher).toHaveBeenCalledWith("/api/v1/workflows/workflow-1/control-evaluations",
    { headers: { "X-Control-Reader": "true" } });
  fireEvent.click(screen.getByRole("button", { name: "Load evaluations" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("403");
  expect(screen.queryByText("Evaluation evaluation-1")).not.toBeInTheDocument();
});
