export type EvidenceMetadata = {
  evidence_id?: string;
  file_name: string;
  content_type: string;
  size_bytes: number;
  checksum_sha256: string;
  uploader_ref: string;
  uploaded_at?: string;
};

export type ProviderContext = {
  provider_context_id: string;
  provider_name: string;
  source_record_ref: string;
  record_type: string;
  payload_json: Record<string, unknown>;
  response_hash: string;
  response_version: string;
  correlation_id: string;
  retrieved_at: string;
};

export type TimelineEntry = {
  timeline_entry_id: string;
  event_type: string;
  message: string;
  audit_event_id: string | null;
  correlation_id: string;
  occurred_at: string;
};

export type AuditEvent = {
  audit_event_id: string;
  event_type: string;
  actor_type: string;
  actor_ref: string;
  source: string;
  object_ref: string | null;
  correlation_id: string;
  created_at: string;
};

export type DisputeCase = {
  case_id: string;
  customer_ref: string;
  account_ref: string | null;
  transaction_ref: string;
  channel: string;
  dispute_type: string;
  description: string;
  status: string;
  correlation_id: string;
  created_at: string;
  timeline: TimelineEntry[];
  evidence_metadata: EvidenceMetadata[];
  provider_context: ProviderContext[];
  audit_events: AuditEvent[];
};

export type CreateDisputeInput = {
  customer_ref: string;
  account_ref: string;
  transaction_ref: string;
  channel: string;
  description: string;
  dispute_type: string;
  evidence_metadata: EvidenceMetadata[];
};

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

async function apiError(response: Response, action: string): Promise<Error> {
  let detail = "";
  try {
    const body = (await response.json()) as {
      detail?: string | { message?: string };
      message?: string;
    };
    if (typeof body.detail === "string") {
      detail = body.detail;
    } else if (body.detail?.message) {
      detail = body.detail.message;
    } else if (body.message) {
      detail = body.message;
    }
  } catch {
    // The status remains actionable when an upstream response has no JSON body.
  }

  const suffix = detail ? `: ${detail}` : "";
  return new Error(`${action} failed (${response.status})${suffix}`);
}

export async function createDispute(
  input: CreateDisputeInput,
  idempotencyKey: string,
  correlationId?: string
): Promise<DisputeCase> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "Idempotency-Key": idempotencyKey
  };
  if (correlationId) {
    headers["X-Correlation-ID"] = correlationId;
  }
  const response = await fetch(`${API_BASE}/api/v1/disputes`, {
    method: "POST",
    headers,
    body: JSON.stringify(input)
  });
  if (!response.ok) {
    throw await apiError(response, "Create dispute");
  }
  return response.json() as Promise<DisputeCase>;
}

export async function getDispute(caseId: string): Promise<DisputeCase> {
  const response = await fetch(`${API_BASE}/api/v1/disputes/${caseId}`);
  if (!response.ok) {
    throw await apiError(response, "Load dispute");
  }
  return response.json() as Promise<DisputeCase>;
}
