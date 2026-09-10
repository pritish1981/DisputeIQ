export type ControlEvaluation = {
  evaluation_id: string;
  bundle: {
    profile_version: string | null; evaluated_at: string; versions: Record<string, string>;
    prior_evaluation_id: string | null; inputs_hash: string; classification_hash: string;
  };
  stages: {
    evidence?: {
      required: string[]; available: string[]; missing: string[]; stale: string[];
      invalid: string[]; conflicting: string[]; satisfaction: Record<string, string[]>;
      mandatory_complete: boolean; score: string; reasons: string[];
    };
    policy?: {
      approved_context: boolean; corpus_version?: string; index_version?: string;
      citations: { document_id: string; version: string; section: string; chunk_hash: string }[];
      reasons: string[];
    };
    rules?: {
      candidate: string; blocked: boolean;
      results: { rule_id: string; version: string; outcome: string; reason_code: string }[];
    };
    confidence?: {
      score: string; threshold: string; ready: boolean; reasons: string[];
      factors: Record<string, {
        raw: string | null; normalized: string; weight: string; contribution: string;
        source_ref: string; valid: boolean;
      }>;
    };
  };
  requests: { request_id: string; kind: string; status: string; reasons: string[] }[];
};

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";
async function read<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}/api/v1/workflows/${path}`, {
    headers: { "X-Control-Reader": "true" }
  });
  if (!response.ok) throw new Error(`Control evaluation lookup failed (${response.status}).`);
  return response.json() as Promise<T>;
}
export function listControlEvaluations(workflowId: string) {
  return read<{ items: ControlEvaluation[] }>(`${encodeURIComponent(workflowId)}/control-evaluations`);
}
export function getControlEvaluation(workflowId: string, evaluationId: string) {
  return read<ControlEvaluation>(
    `${encodeURIComponent(workflowId)}/control-evaluations/${encodeURIComponent(evaluationId)}`
  );
}
